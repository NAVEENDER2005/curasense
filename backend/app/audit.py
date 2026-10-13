"""Every PHI-touching read/write logs an audit_logs row: who, what action, on
what resource, whether PHI was involved - never the PHI content itself, so
audit_logs is always safe to export or query without a separate PHI review.
"""
import asyncpg


async def log_action(pool: asyncpg.Pool, *, user_id: str | None, action: str, resource_type: str,
                      resource_id: str | None, phi_accessed: bool, details: dict | None = None) -> None:
    await pool.execute(
        """
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, phi_accessed, details)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        """,
        user_id, action, resource_type, resource_id, phi_accessed, details or {},
    )
