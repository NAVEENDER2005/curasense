"""Shared revenue/claims aggregate computation, used by the dashboard router
and by Ask My Data (ai.chat) - a single source of truth for the numbers so the
chat answers and the dashboard KPIs can never silently disagree.
"""
from app.db import row_to_dict, rows_to_list


async def compute_summary(pool) -> dict:
    kpis = row_to_dict(await pool.fetchrow(
        """
        SELECT
            COALESCE(sum(total_billed), 0) AS total_billed,
            COALESCE(sum(total_billed) FILTER (WHERE status = 'denied'), 0) AS total_denied_amount,
            count(*) FILTER (WHERE status = 'denied') AS denied_count,
            count(*) FILTER (WHERE status IN ('denied', 'paid')) AS decided_count,
            count(*) FILTER (WHERE status = 'ready') AS ready_count,
            count(*) FILTER (WHERE status = 'recovered') AS recovered_count
        FROM claims
        """
    ))
    denial_rate = (kpis["denied_count"] / kpis["decided_count"]) if kpis["decided_count"] else 0.0

    revenue_at_risk = await pool.fetchval(
        """
        SELECT COALESCE(sum(c.total_billed), 0)
        FROM claims c
        JOIN LATERAL (
            SELECT risk_level FROM denial_scores WHERE claim_id = c.id ORDER BY scored_at DESC LIMIT 1
        ) ds ON true
        WHERE c.status IN ('ready', 'submitted') AND ds.risk_level = 'high'
        """
    )

    risk_distribution = rows_to_list(await pool.fetch(
        """
        SELECT ds.risk_level, count(*) AS claim_count
        FROM claims c
        JOIN LATERAL (
            SELECT risk_level FROM denial_scores WHERE claim_id = c.id ORDER BY scored_at DESC LIMIT 1
        ) ds ON true
        WHERE c.status IN ('ready', 'submitted')
        GROUP BY ds.risk_level
        """
    ))

    denials_by_payer = rows_to_list(await pool.fetch(
        """
        SELECT pay.name AS payer_name, count(*) AS denial_count, COALESCE(sum(c.total_billed), 0) AS denied_amount
        FROM claims c JOIN payers pay ON pay.id = c.payer_id
        WHERE c.status = 'denied'
        GROUP BY pay.name ORDER BY denied_amount DESC
        """
    ))

    recent_denials = rows_to_list(await pool.fetch(
        """
        SELECT c.claim_number, pay.name AS payer_name, c.denial_reason, c.total_billed, c.decided_at
        FROM claims c JOIN payers pay ON pay.id = c.payer_id
        WHERE c.status = 'denied'
        ORDER BY c.decided_at DESC LIMIT 10
        """
    ))

    return {
        "kpis": {**kpis, "denial_rate": denial_rate, "revenue_at_risk": revenue_at_risk},
        "risk_distribution": risk_distribution,
        "denials_by_payer": denials_by_payer,
        "recent_denials": recent_denials,
    }


def flatten_for_chat(summary: dict) -> dict:
    """Turns the nested summary into flat key: value lines that read well
    inside an LLM prompt (ai.chat.build_context)."""
    k = summary["kpis"]
    flat = {
        "total_billed_all_claims": f"₹{k['total_billed']:,.2f}",
        "total_denied_amount": f"₹{k['total_denied_amount']:,.2f}",
        "denial_rate": f"{k['denial_rate']:.1%}",
        "revenue_at_risk_high_risk_pending_claims": f"₹{k['revenue_at_risk']:,.2f}",
        "claims_pending_submission": k["ready_count"],
        "claims_recovered_via_appeal": k["recovered_count"],
    }
    for row in summary["risk_distribution"]:
        flat[f"pending_claims_risk_level_{row['risk_level']}"] = row["claim_count"]
    for row in summary["denials_by_payer"]:
        flat[f"denials_by_payer_{row['payer_name']}"] = f"{row['denial_count']} claims, ₹{row['denied_amount']:,.2f}"
    for row in summary["recent_denials"]:
        flat[f"recent_denial_{row['claim_number']}"] = f"{row['payer_name']}, ₹{row['total_billed']:,.2f} - {row['denial_reason']}"
    return flat
