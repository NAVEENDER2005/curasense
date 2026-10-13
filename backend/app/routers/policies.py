from typing import Optional

from fastapi import APIRouter, Depends, Query

from ai.rag import retrieve_relevant_policies
from app.dependencies import get_pool
from app.db import rows_to_list

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("")
async def list_policies(payer_code: Optional[str] = None, pool=Depends(get_pool)):
    rows = await pool.fetch(
        """
        SELECT pp.id, pay.payer_code, pay.name AS payer_name, pp.policy_number, pp.title,
               pp.category, pp.content, pp.effective_date
        FROM payer_policies pp JOIN payers pay ON pay.id = pp.payer_id
        WHERE ($1::text IS NULL OR pay.payer_code = $1)
        ORDER BY pay.payer_code, pp.policy_number
        """,
        payer_code,
    )
    return rows_to_list(rows)


@router.get("/search")
async def search_policies(q: str = Query(..., min_length=2), payer_code: str = Query(...), top_k: int = 5):
    """Policy Intelligence: RAG-based search so billing staff can instantly
    verify clinical necessity language against a specific payer's rules."""
    return retrieve_relevant_policies(query_text=q, payer_code=payer_code, top_k=top_k)
