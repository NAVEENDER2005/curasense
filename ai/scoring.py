"""Predictive Denial Engine: scores a claim for denial risk before it leaves
the hospital system, using RAG-retrieved payer policy checks (ai.policy_rules)
plus historical denial-rate data for the same payer/diagnosis combination.

Deliberately rule-based and fully explainable (not a black-box model) - each
point on the score traces to a specific, citable reason. See ai/README.md for
the upgrade path to a trained ML model once real claims history accumulates.
"""
from ai.policy_rules import evaluate_policies
from ai.rag import retrieve_relevant_policies

SEVERITY_WEIGHTS = {"high": 55, "medium": 28, "low": 0, "info": 0}
FRAUD_SEVERITY_WEIGHTS = {"high": 40, "medium": 20, "low": 8}
BASE_SCORE = 8
HIGH_RISK_THRESHOLD = 55
MEDIUM_RISK_THRESHOLD = 25


def score_claim(claim: dict, note_text: str, payer_code: str,
                 historical_denial_rate: float | None = None,
                 fraud_flags: list[dict] | None = None) -> dict:
    """
    claim: {icd10_codes, cpt_codes, ...}
    note_text: clinical note / discharge summary content
    historical_denial_rate: 0-1 fraction of similar past claims (same payer)
        that were denied, if known
    fraud_flags: output of ai.fraud.scan_claim, if already computed
    """
    query_text = f"{' '.join(claim['icd10_codes'])} {' '.join(claim['cpt_codes'])} {note_text}"
    retrieved = retrieve_relevant_policies(query_text, payer_code=payer_code, top_k=4)
    policy_checks = evaluate_policies(claim, note_text, retrieved)

    score = BASE_SCORE
    reasons = []
    positive_findings = []

    for check in policy_checks:
        if check["passed"] is False:
            score += SEVERITY_WEIGHTS.get(check["severity"], 0)
            reasons.append({
                "severity": check["severity"],
                "message": check["message"],
                "suggested_action": check.get("suggested_action"),
                "suggested_code": check.get("suggested_code"),
                "policy_citation": {"policy_number": check["policy_number"], "title": check["title"]},
            })
        elif check["passed"] is True:
            positive_findings.append({
                "message": check["message"],
                "policy_citation": {"policy_number": check["policy_number"], "title": check["title"]},
            })

    if historical_denial_rate is not None:
        historical_contribution = round(historical_denial_rate * 25)
        if historical_contribution > 0:
            score += historical_contribution
            reasons.append({
                "severity": "medium" if historical_denial_rate >= 0.3 else "low",
                "message": (f"Similar claims to this payer have historically been denied "
                            f"{historical_denial_rate:.0%} of the time."),
                "suggested_action": None, "suggested_code": None, "policy_citation": None,
            })

    for flag in (fraud_flags or []):
        score += FRAUD_SEVERITY_WEIGHTS.get(flag["severity"], 15)
        reasons.append({
            "severity": flag["severity"], "message": f"Compliance flag ({flag['flag_type']}): {flag['description']}",
            "suggested_action": "Review before submission - may trigger payer audit.",
            "suggested_code": None, "policy_citation": None,
        })

    score = max(0, min(100, score))
    if score >= HIGH_RISK_THRESHOLD:
        risk_level = "high"
    elif score >= MEDIUM_RISK_THRESHOLD:
        risk_level = "medium"
    else:
        risk_level = "low"

    reasons.sort(key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r["severity"], 3))

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "reasons": reasons,
        "positive_findings": positive_findings,
        "policy_citations": [
            {"policy_number": c["policy_number"], "title": c["title"], "relevance_score": c["relevance_score"]}
            for c in policy_checks
        ],
        "model_version": "rule-engine-v1",
    }
