"""Denial Explainer: turns a denial-risk score's structured reasons into a
clear, human-readable explanation for billing staff - the risk score is never
shown without the "why" behind it.
"""
from ai import config
from ai.llm import complete_reasoning

SEVERITY_LABEL = {"high": "Critical", "medium": "Moderate", "low": "Minor"}


def explain_score(score_result: dict) -> dict:
    bullets = []
    for reason in score_result["reasons"]:
        citation = reason.get("policy_citation")
        cite_text = f" (per {citation['policy_number']}: {citation['title']})" if citation else ""
        bullet = f"**{SEVERITY_LABEL.get(reason['severity'], 'Note')}:** {reason['message']}{cite_text}"
        if reason.get("suggested_action"):
            bullet += f" → *{reason['suggested_action']}*"
        bullets.append(bullet)

    for finding in score_result.get("positive_findings", []):
        citation = finding.get("policy_citation")
        cite_text = f" (per {citation['policy_number']})" if citation else ""
        bullets.append(f"✓ {finding['message']}{cite_text}")

    narrative = None
    if config.HAS_ANTHROPIC:
        narrative = complete_reasoning(
            system=("You are a healthcare RCM analyst. Given a claim's structured denial-risk reasons, "
                     "write a 2-sentence executive summary for a CFO dashboard. Be concrete, not vague."),
            user="\n".join(bullets),
        )

    return {
        "risk_level": score_result["risk_level"],
        "risk_score": score_result["risk_score"],
        "bullets": bullets,
        "executive_summary": narrative,
    }
