import uuid

from fastapi import APIRouter, Depends, HTTPException

from ai.appeals import draft_appeal
from app.audit import log_action
from app.dependencies import CurrentUser, get_current_user, get_pool
from app.db import rows_to_list, row_to_dict

router = APIRouter(prefix="/appeals", tags=["appeals"])


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"invalid id: {value}")


@router.get("")
async def list_appeals(pool=Depends(get_pool)):
    rows = await pool.fetch(
        """
        SELECT c.id AS claim_id, c.claim_number, c.denial_reason, c.total_billed, c.decided_at,
               pay.name AS payer_name, p.first_name, p.last_name,
               al.id AS appeal_id, al.status AS appeal_status, al.generated_at
        FROM claims c
        JOIN encounters enc ON enc.id = c.encounter_id
        JOIN patients p ON p.id = enc.patient_id
        JOIN payers pay ON pay.id = c.payer_id
        LEFT JOIN LATERAL (
            SELECT id, status, generated_at FROM appeal_letters WHERE claim_id = c.id ORDER BY generated_at DESC LIMIT 1
        ) al ON true
        WHERE c.status = 'denied'
        ORDER BY c.decided_at DESC
        """
    )
    return rows_to_list(rows)


@router.post("/{claim_id}/generate")
async def generate_appeal(claim_id: str, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    cid = _parse_uuid(claim_id)
    claim = row_to_dict(await pool.fetchrow(
        """
        SELECT c.id, c.claim_number, c.icd10_codes, c.cpt_codes, c.denial_reason, c.encounter_id,
               pay.payer_code, p.first_name, p.last_name
        FROM claims c
        JOIN encounters enc ON enc.id = c.encounter_id
        JOIN patients p ON p.id = enc.patient_id
        JOIN payers pay ON pay.id = c.payer_id
        WHERE c.id = $1 AND c.status = 'denied'
        """,
        cid,
    ))
    if claim is None:
        raise HTTPException(status_code=404, detail="denied claim not found")

    note = await pool.fetchval(
        "SELECT content FROM clinical_notes WHERE encounter_id = $1 ORDER BY created_at LIMIT 1", claim["encounter_id"],
    )
    if note is None:
        raise HTTPException(status_code=422, detail="no clinical note available for this claim's encounter")

    patient_name = f"{claim['first_name']} {claim['last_name']}"
    result = draft_appeal(claim, patient_name, note, claim["denial_reason"] or "", claim["payer_code"])

    row = await pool.fetchrow(
        """
        INSERT INTO appeal_letters (claim_id, denial_reason, letter_content, evidence_used, status)
        VALUES ($1, $2, $3, $4::jsonb, 'draft')
        RETURNING id, denial_reason, letter_content, evidence_used, status, generated_at
        """,
        cid, claim["denial_reason"], result["letter_content"], result["evidence_used"],
    )

    await log_action(pool, user_id=None, action="generate_appeal", resource_type="claim",
                      resource_id=str(cid), phi_accessed=True, details={"model_used": result["model_used"]})

    return {**row_to_dict(row), "model_used": result["model_used"]}


@router.get("/{claim_id}")
async def get_appeal(claim_id: str, pool=Depends(get_pool)):
    cid = _parse_uuid(claim_id)
    rows = rows_to_list(await pool.fetch(
        "SELECT id, denial_reason, letter_content, evidence_used, status, generated_at FROM appeal_letters WHERE claim_id = $1 ORDER BY generated_at DESC",
        cid,
    ))
    return rows


@router.patch("/letter/{letter_id}/status")
async def update_appeal_status(letter_id: str, status: str, pool=Depends(get_pool)):
    if status not in {"draft", "reviewed", "sent"}:
        raise HTTPException(status_code=400, detail="invalid status")
    lid = _parse_uuid(letter_id)
    row = await pool.fetchrow(
        "UPDATE appeal_letters SET status = $2 WHERE id = $1 RETURNING id, status", lid, status,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="appeal letter not found")
    return row_to_dict(row)
