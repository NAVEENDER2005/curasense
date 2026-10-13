"""Ask My Data: natural-language Q&A over revenue/claims data for CFOs and
administrators.

Deliberately NOT text-to-SQL: the LLM never generates or executes queries
against the database (that would be an injection and data-exposure risk for
a system holding PHI-adjacent financial data). Instead the backend computes a
fixed set of revenue aggregates (ai.chat.build_context) and the LLM answers
grounded only in that pre-computed, already-authorized context.
"""
import re

from ai import config
from ai.llm import complete_reasoning


def build_context(claims_summary: dict) -> str:
    """claims_summary: aggregate stats computed by the backend from SQL
    (never raw per-patient rows) - e.g. totals, rates, breakdowns by payer."""
    lines = [f"{k}: {v}" for k, v in claims_summary.items()]
    return "\n".join(lines)


def _dollar_amount(text: str) -> float:
    match = re.search(r"\$([\d,]+(?:\.\d+)?)", text)
    return float(match.group(1).replace(",", "")) if match else 0.0


def _offline_answer(question: str, context: dict) -> str | None:
    """Answers a handful of common questions directly from the pre-computed
    aggregates, without an LLM - so the offline demo reads like a real answer
    instead of a raw data dump. Falls through (returns None) for anything it
    doesn't recognize; the caller then shows the full context instead."""
    q = question.lower()

    if "denial rate" in q or ("how many" in q and "den" in q):
        return (f"Your current denial rate is {context.get('denial_rate', 'unknown')} - "
                f"{context.get('total_denied_amount', '?')} denied out of "
                f"{context.get('total_billed_all_claims', '?')} billed.")

    if "at risk" in q:
        high = context.get("pending_claims_risk_level_high", 0)
        return (f"{context.get('revenue_at_risk_high_risk_pending_claims', '?')} is currently at risk, "
                f"across {high} high-risk claim(s) that haven't been paid yet.")

    if "payer" in q and any(w in q for w in ["most", "worst", "denies", "denying"]):
        payer_rows = {k[len("denials_by_payer_"):]: v for k, v in context.items() if k.startswith("denials_by_payer_")}
        if not payer_rows:
            return "No denials on file for any payer yet."
        worst_payer, worst_desc = max(payer_rows.items(), key=lambda kv: _dollar_amount(kv[1]))
        return f"{worst_payer} has the most denied revenue: {worst_desc}."

    if "recover" in q:
        return f"{context.get('claims_recovered_via_appeal', 0)} claim(s) have been recovered via appeal so far."

    if "pending" in q or "not yet submitted" in q or "ready" in q:
        return f"{context.get('claims_pending_submission', 0)} claim(s) are pending submission."

    return None


_DATA_KEYWORDS = ("denial", "denied", "revenue", "payer", "claim", "billed", "risk", "recover", "appeal", "money", "$")


def _looks_like_data_question(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _DATA_KEYWORDS)


def answer_question(question: str, claims_summary: dict) -> str:
    if config.HAS_ANTHROPIC:
        context = build_context(claims_summary)
        return complete_reasoning(
            system=("You are CuraSense's revenue analytics assistant. Answer the CFO's question using ONLY "
                     "the data provided below - never invent numbers. If the data doesn't contain the answer, "
                     "say so and suggest what data would be needed. Be concise (2-4 sentences), lead with the number."),
            user=f"Revenue/claims data:\n{context}\n\nQuestion: {question}",
        )

    offline = _offline_answer(question, claims_summary)
    if offline:
        return offline

    if not _looks_like_data_question(question):
        return ("I can answer questions about revenue, denials, payers, and claims — try asking "
                "\"What is our denial rate?\", \"How much revenue is at risk?\", or \"Which payer denies "
                "the most revenue?\".")

    formatted_lines = []
    for k, v in claims_summary.items():
        title = k.replace("_", " ").title()
        formatted_lines.append(f"• **{title}:** {v}")
    
    return f"Here is the revenue cycle summary related to your inquiry:\n\n" + "\n".join(formatted_lines)
