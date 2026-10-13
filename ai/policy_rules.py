"""Codified checks for the payer policies in the sample corpus.

Each rule says: "if this policy applies to this claim, does the clinical note
+ coded claim satisfy it?" This is intentionally a small, transparent
rule-based v1 (per the build spec: 'start rule-based/simple ML, upgrade to
full model later') rather than an opaque model - every risk reason the
scoring engine produces traces back to one of these functions plus the
specific policy text that was retrieved via RAG, so nothing is a black box.
"""
import re

# Naive substring matching treats "no trauma" the same as "trauma" - wrong for
# clinical text, where negated findings are exactly as common as positive
# ones. Every phrase match below is rejected if a negation marker appears
# shortly before it in the same sentence.
NEGATION_MARKERS = ["no ", "not ", "denies", "denied", "without ", "negative for",
                     "no evidence of", "absence of", "ruled out", "lack of"]


def _mentioned_positively(text: str, phrase: str, window: int = 25) -> bool:
    lowered = text.lower()
    phrase = phrase.lower()
    start = 0
    while True:
        idx = lowered.find(phrase, start)
        if idx == -1:
            return False
        preceding = lowered[max(0, idx - window):idx]
        if not any(neg in preceding for neg in NEGATION_MARKERS):
            return True
        start = idx + len(phrase)


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(_mentioned_positively(text, p) for p in phrases)


def _has_code_prefix(codes: list[str], prefixes: list[str]) -> bool:
    return any(any(code.startswith(p) for p in prefixes) for code in codes)


def _count_code(codes: list[str], code: str) -> int:
    return sum(1 for c in codes if c == code)


def rule_sepsis_organ_dysfunction(claim: dict, note_text: str) -> dict | None:
    if not _has_code_prefix(claim["icd10_codes"], ["A41", "A40"]):
        return None
    mentions_dysfunction = _has_any(
        note_text, ["organ dysfunction", "acute kidney injury", "aki", "altered mental status",
                    "elevated lactate", "hypotension"]
    )
    has_linked_code = _has_code_prefix(claim["icd10_codes"], ["N17", "R65.2", "J96", "R41"])
    if mentions_dysfunction and not has_linked_code:
        return {
            "passed": False, "severity": "high",
            "message": ("Note documents organ dysfunction (e.g. acute kidney injury) but no linked "
                        "organ-dysfunction ICD-10 code is present on the claim. Payer requires an explicit "
                        "linked diagnosis code for the severe sepsis reimbursement tier."),
            "suggested_action": "Add a linked organ-dysfunction code (e.g. N17.9) cross-referenced to the septic episode.",
        }
    if mentions_dysfunction and has_linked_code:
        return {"passed": True, "severity": "low",
                "message": "Organ dysfunction is documented and linked with a specific ICD-10 code, satisfying severity-of-illness requirements."}
    return {"passed": False, "severity": "medium",
            "message": "Sepsis coded but note does not clearly document SIRS criteria or organ dysfunction linkage.",
            "suggested_action": "Confirm SIRS criteria and organ dysfunction are documented before submission."}


def rule_lumbar_mri_conservative_therapy(claim: dict, note_text: str) -> dict | None:
    if not _has_code_prefix(claim["cpt_codes"], ["72148"]):
        return None
    red_flags = _has_any(note_text, ["cauda equina", "progressive neurological deficit", "malignancy", "infection", "trauma"])
    conservative = _has_any(note_text, ["physical therapy", "nsaid", "corticosteroid", "conservative therapy", "conservative management"])
    if red_flags:
        return {"passed": True, "severity": "low",
                "message": "Red-flag symptoms documented, exempting this order from the conservative-therapy trial requirement."}
    if conservative:
        week_match = re.search(r"(\d+)\s*week", note_text.lower())
        weeks = int(week_match.group(1)) if week_match else 0
        if weeks >= 6:
            return {"passed": True, "severity": "low",
                    "message": f"Documented {weeks}-week conservative therapy trial satisfies prior-authorization requirement."}
    return {"passed": False, "severity": "high",
            "message": ("No red-flag symptoms and no adequately documented conservative therapy trial (policy "
                        "requires 6+ weeks) - payer will deny for lack of medical necessity."),
            "suggested_action": "Document a 6-week conservative therapy trial or the specific red-flag symptom justifying expedited imaging before submitting."}


def rule_chf_specificity(claim: dict, note_text: str) -> dict | None:
    if "I50.9" not in claim["icd10_codes"]:
        return None
    specificity_markers = _has_any(note_text, ["lvef", "ejection fraction", "systolic", "diastolic", "acute on chronic", "acute decompensation"])
    if specificity_markers:
        suggested = "I50.23" if _has_any(note_text, ["systolic", "acute on chronic", "acute decompensation"]) else "I50.33"
        return {"passed": False, "severity": "medium",
                "message": ("Diagnosis coded as unspecified heart failure (I50.9), but the note documents "
                             "echocardiogram findings and acuity supporting a more specific code."),
                "suggested_action": f"Recode to {suggested} to match documented specificity and avoid coding-review denial.",
                "suggested_code": suggested}
    return {"passed": True, "severity": "low", "message": "No greater specificity documented; I50.9 is appropriately coded."}


def rule_copd_admission_criteria(claim: dict, note_text: str) -> dict | None:
    if not _has_code_prefix(claim["icd10_codes"], ["J44"]):
        return None
    has_spirometry = _has_any(note_text, ["spirometry", "gold stage"])
    has_exacerbation_criteria = _has_any(note_text, ["dyspnea", "sputum", "oxygen requirement", "supplemental oxygen"])
    has_intensity = _has_any(note_text, ["iv methylprednisolone", "iv corticosteroid", "nebulized", "oxygen titration"])
    if has_spirometry and has_exacerbation_criteria and has_intensity:
        return {"passed": True, "severity": "low",
                "message": "Spirometry-confirmed severity, exacerbation criteria, and inpatient-level treatment intensity are all documented - admission is well supported."}
    missing = [name for name, ok in [
        ("spirometry-confirmed severity", has_spirometry),
        ("objective exacerbation criteria", has_exacerbation_criteria),
        ("inpatient-level treatment intensity", has_intensity),
    ] if not ok]
    return {"passed": False, "severity": "medium",
            "message": f"Admission documentation is missing: {', '.join(missing)}.",
            "suggested_action": "Document the missing criteria to support inpatient level of care."}


def rule_repeat_imaging(claim: dict, note_text: str) -> dict | None:
    if _count_code(claim["cpt_codes"], "71046") < 2:
        return None
    mentions_change = _has_any(note_text, ["new hypoxia", "pneumothorax", "clinical change", "acute change"])
    if mentions_change:
        return {"passed": True, "severity": "low", "message": "Repeat imaging is justified by a documented acute clinical change."}
    return {"passed": False, "severity": "high",
            "message": (f"{_count_code(claim['cpt_codes'], '71046')} chest X-rays billed with no documented "
                        "clinical change between studies - Medicare flags this as duplicate billing / unbundling."),
            "suggested_action": "Document the clinical justification for repeat imaging, or remove the duplicate charge before submission."}


def rule_knee_arthroplasty_necessity(claim: dict, note_text: str) -> dict | None:
    if not _has_code_prefix(claim["cpt_codes"], ["27447"]):
        return None
    conservative = _has_any(note_text, ["physical therapy", "nsaid", "corticosteroid injection"])
    month_match = re.search(r"(\d+)\s*month", note_text.lower())
    months = int(month_match.group(1)) if month_match else 0
    if conservative and months >= 3:
        return {"passed": True, "severity": "low",
                "message": f"Documented {months}-month conservative management trial satisfies medical necessity criteria."}
    return {"passed": False, "severity": "medium",
            "message": "Conservative management trial is not clearly documented for at least 3 months.",
            "suggested_action": "Document prior conservative treatment (PT, NSAIDs, injections) and duration."}


# Each rule is scoped to the one policy_number it codifies - a rule must never
# fire for a different policy just because its `applies` condition happens to
# match (e.g. two payers both mentioning heart failure).
POLICY_NUMBER_TO_RULE = {
    "AET-CP-0142": rule_sepsis_organ_dysfunction,
    "AET-CP-0209": rule_lumbar_mri_conservative_therapy,
    "UHC-MP-0088": rule_chf_specificity,
    "UHC-MP-0115": rule_copd_admission_criteria,
    "CMS-LCD-3341": rule_repeat_imaging,
    "CMS-LCD-2207": rule_knee_arthroplasty_necessity,
}


def evaluate_policies(claim: dict, note_text: str, retrieved_policies: list[dict]) -> list[dict]:
    """retrieved_policies: output of ai.rag.retrieve_relevant_policies. Returns
    one entry per retrieved policy: a codified check result if a rule exists
    for it, otherwise a plain citation (informational, not yet codified)."""
    results = []
    for policy in retrieved_policies:
        meta = policy["metadata"]
        rule_fn = POLICY_NUMBER_TO_RULE.get(meta["policy_number"])
        outcome = rule_fn(claim, note_text) if rule_fn else None
        entry = {
            "policy_number": meta["policy_number"],
            "title": meta["title"],
            "category": meta.get("category"),
            "relevance_score": round(policy["score"], 3),
        }
        if outcome is not None:
            entry.update(outcome)
        else:
            entry.update({"passed": None, "severity": "info",
                          "message": "Retrieved as potentially relevant context; no codified check yet for this policy."})
        results.append(entry)
    return results
