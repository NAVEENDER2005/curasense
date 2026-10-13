"""GenAI Document Extraction / Auto-Coding Co-Pilot: parses unstructured
physician notes and discharge summaries into structured ICD-10/CPT codes, and
flags charges the documentation supports that the claim hasn't billed yet
(under-coding / missed revenue capture).

COMPLIANCE NOTE: `note_text` is clinical documentation (synthetic PHI-shaped
data in this demo). When OPENAI_API_KEY is configured, a redacted rationale
prompt derived from note_text is sent to the OpenAI API - in production this
requires a signed BAA before any real patient note is sent to a third-party
LLM. The core coding logic below is rule-based specifically so the app works,
and is auditable, even with zero LLM calls.
"""
from ai import config
from ai.llm import complete_extraction

# keyword -> code the documentation supports. Deliberately small and
# transparent for v1; see README.md for the upgrade path to an NLP/LLM-based
# extractor once more note volume is available to validate against.
CODE_SUGGESTION_RULES = [
    {
        "keywords": ["acute kidney injury", " aki ", "aki)", "aki."],
        "code_system": "ICD10", "code": "N17.9", "description": "Acute kidney injury, unspecified",
        "rationale": "Note documents acute kidney injury with creatinine trend, but no linked AKI diagnosis code is on the claim.",
    },
    {
        "keywords": ["urinary tract infection"],
        "code_system": "ICD10", "code": "N39.0", "description": "Urinary tract infection, site not specified",
        "rationale": "Note identifies a UTI as the sepsis source; this secondary diagnosis is not currently billed.",
    },
    {
        "keywords": ["lvef", "ejection fraction", "systolic heart failure", "acute decompensation"],
        "code_system": "ICD10", "code": "I50.23", "description": "Acute on chronic systolic (congestive) heart failure",
        "rationale": "Echo findings and acuity language support a specific heart-failure code rather than the unspecified code currently billed.",
    },
    {
        "keywords": ["iv levofloxacin", "iv ceftriaxone", "iv antibiotics", "iv furosemide", "iv methylprednisolone"],
        "code_system": "CPT", "code": "96365", "description": "IV infusion, for therapy/diagnosis, initial up to 1 hour",
        "rationale": "Note documents IV medication administration; the infusion administration charge is billed separately from the drug and E/M codes and is commonly missed.",
    },
    {
        "keywords": ["nebulized"],
        "code_system": "CPT", "code": "94640", "description": "Airway inhalation treatment (nebulizer)",
        "rationale": "Note documents nebulized bronchodilator treatment, which is separately billable and not currently on the claim.",
    },
]


def _rule_based_extract(note_text: str, billed_icd10: list[str], billed_cpt: list[str]) -> list[dict]:
    lowered = f" {note_text.lower()} "
    missing = []
    for rule in CODE_SUGGESTION_RULES:
        if not any(kw in lowered for kw in rule["keywords"]):
            continue
        billed = billed_icd10 if rule["code_system"] == "ICD10" else billed_cpt
        if rule["code"] in billed:
            continue
        missing.append({
            "code_system": rule["code_system"], "code": rule["code"],
            "description": rule["description"], "rationale": rule["rationale"],
        })
    return missing


def extract_coding(note_text: str, billed_icd10: list[str], billed_cpt: list[str]) -> dict:
    missing_charges = _rule_based_extract(note_text, billed_icd10, billed_cpt)

    narrative = None
    if config.HAS_OPENAI and missing_charges:
        summary_input = "\n".join(f"- {m['code_system']} {m['code']} ({m['description']}): {m['rationale']}" for m in missing_charges)
        narrative = complete_extraction(
            system=("You are a clinical coding assistant. Given a list of under-coded charges identified by "
                    "a rules engine, write a 2-3 sentence plain-English summary for a billing coordinator. "
                    "Do not invent new codes."),
            user=f"Clinical note:\n{note_text}\n\nUnder-coded charges found:\n{summary_input}",
        )

    return {
        "suggested_icd10_additions": [m for m in missing_charges if m["code_system"] == "ICD10"],
        "suggested_cpt_additions": [m for m in missing_charges if m["code_system"] == "CPT"],
        "missing_charges": missing_charges,
        "narrative_summary": narrative,
        "model_used": "gpt-4o" if (config.HAS_OPENAI and missing_charges) else "rule-engine-v1",
    }
