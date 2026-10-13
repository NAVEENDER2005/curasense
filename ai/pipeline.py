"""Combines fraud scan + denial scoring + explanation + coding extraction into
one call - the full "ingest -> score -> explain" pipeline for a single claim.
Shared by the live scoring API route and the batch pre-scoring script so the
two never drift apart.
"""
from ai.explainer import explain_score
from ai.extraction import extract_coding
from ai.fraud import scan_claim
from ai.scoring import score_claim


def run_pipeline(claim: dict, note_text: str, payer_code: str, historical_denial_rate: float | None = None) -> dict:
    fraud_flags = scan_claim(claim)
    score_result = score_claim(claim, note_text, payer_code,
                                historical_denial_rate=historical_denial_rate, fraud_flags=fraud_flags)
    explanation = explain_score(score_result)
    extraction_result = extract_coding(note_text, claim["icd10_codes"], claim["cpt_codes"])

    reasons_payload = {
        "raw_reasons": score_result["reasons"],
        "positive_findings": score_result["positive_findings"],
        "bullets": explanation["bullets"],
        "executive_summary": explanation["executive_summary"],
    }

    return {
        "score_result": score_result,
        "explanation": explanation,
        "extraction_result": extraction_result,
        "fraud_flags": fraud_flags,
        "reasons_payload": reasons_payload,
    }
