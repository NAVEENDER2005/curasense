import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ai.pipeline import run_pipeline
from app.audit import log_action
from app.dependencies import CurrentUser, get_current_user, get_pool
from app.db import rows_to_list, row_to_dict

router = APIRouter(prefix="/claims", tags=["claims"])


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"invalid id: {value}")


LIST_QUERY = """
SELECT c.id, c.claim_number, c.status, c.total_billed, c.icd10_codes, c.cpt_codes,
       c.denial_reason, c.submitted_at, c.decided_at, c.created_at,
       p.first_name, p.last_name, p.mrn,
       pay.name AS payer_name, pay.payer_code,
       enc.encounter_type, enc.department, enc.attending_physician,
       ds.risk_score, ds.risk_level, ds.scored_at
FROM claims c
JOIN encounters enc ON enc.id = c.encounter_id
JOIN patients p ON p.id = enc.patient_id
JOIN payers pay ON pay.id = c.payer_id
LEFT JOIN LATERAL (
    SELECT risk_score, risk_level, scored_at FROM denial_scores
    WHERE claim_id = c.id ORDER BY scored_at DESC LIMIT 1
) ds ON true
WHERE ($1::text IS NULL OR c.status = $1)
  AND ($2::text IS NULL OR ds.risk_level = $2)
  AND ($3::text IS NULL OR pay.payer_code = $3)
ORDER BY c.created_at DESC
"""


@router.get("")
async def list_claims(status: Optional[str] = None, risk_level: Optional[str] = None,
                       payer_code: Optional[str] = None, pool=Depends(get_pool)):
    rows = await pool.fetch(LIST_QUERY, status, risk_level, payer_code)
    return rows_to_list(rows)


@router.get("/{claim_id}")
async def get_claim(claim_id: str, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    cid = _parse_uuid(claim_id)
    claim = row_to_dict(await pool.fetchrow(
        """
        SELECT c.*, pay.name AS payer_name, pay.payer_code,
               enc.encounter_type, enc.department, enc.attending_physician, enc.admit_date, enc.discharge_date,
               p.first_name, p.last_name, p.mrn, p.date_of_birth
        FROM claims c
        JOIN encounters enc ON enc.id = c.encounter_id
        JOIN patients p ON p.id = enc.patient_id
        JOIN payers pay ON pay.id = c.payer_id
        WHERE c.id = $1
        """,
        cid,
    ))
    if claim is None:
        raise HTTPException(status_code=404, detail="claim not found")

    notes = rows_to_list(await pool.fetch(
        "SELECT id, note_type, author, content, created_at FROM clinical_notes WHERE encounter_id = $1 ORDER BY created_at",
        claim["encounter_id"],
    ))
    latest_score = row_to_dict(await pool.fetchrow(
        "SELECT risk_score, risk_level, reasons, policy_citations, model_version, scored_at FROM denial_scores WHERE claim_id = $1 ORDER BY scored_at DESC LIMIT 1",
        cid,
    ))
    latest_extraction = None
    if notes:
        latest_extraction = row_to_dict(await pool.fetchrow(
            """
            SELECT icd10_codes, cpt_codes, missing_charges, model_used, created_at
            FROM extracted_codings WHERE note_id = $1 ORDER BY created_at DESC LIMIT 1
            """,
            notes[0]["id"],
        ))
    fraud_flags = rows_to_list(await pool.fetch(
        "SELECT flag_type, severity, description, detected_at FROM fraud_flags WHERE claim_id = $1 ORDER BY detected_at DESC",
        cid,
    ))
    appeal = row_to_dict(await pool.fetchrow(
        "SELECT id, denial_reason, letter_content, evidence_used, status, generated_at FROM appeal_letters WHERE claim_id = $1 ORDER BY generated_at DESC LIMIT 1",
        cid,
    ))

    await log_action(pool, user_id=None, action="view_claim_detail", resource_type="claim",
                      resource_id=str(cid), phi_accessed=True, details={"role": user.role})

    return {
        "claim": claim, "notes": notes, "latest_score": latest_score,
        "latest_extraction": latest_extraction, "fraud_flags": fraud_flags, "appeal": appeal,
    }


@router.post("/{claim_id}/score")
async def run_scoring(claim_id: str, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    cid = _parse_uuid(claim_id)
    claim = row_to_dict(await pool.fetchrow(
        """
        SELECT c.id, c.encounter_id, c.payer_id, c.icd10_codes, c.cpt_codes, c.total_billed, c.status,
               pay.payer_code
        FROM claims c JOIN payers pay ON pay.id = c.payer_id
        WHERE c.id = $1
        """,
        cid,
    ))
    if claim is None:
        raise HTTPException(status_code=404, detail="claim not found")

    note = row_to_dict(await pool.fetchrow(
        "SELECT id, content FROM clinical_notes WHERE encounter_id = $1 ORDER BY created_at LIMIT 1",
        claim["encounter_id"],
    ))
    if note is None:
        raise HTTPException(status_code=422, detail="no clinical note available for this claim's encounter")

    historical_denial_rate = await pool.fetchval(
        """
        SELECT CASE WHEN count(*) FILTER (WHERE status IN ('denied', 'paid')) = 0 THEN NULL
               ELSE count(*) FILTER (WHERE status = 'denied')::float
                    / count(*) FILTER (WHERE status IN ('denied', 'paid'))
               END
        FROM claims WHERE payer_id = $1 AND id != $2
        """,
        claim["payer_id"], cid,
    )

    pipeline_result = run_pipeline(claim, note["content"], claim["payer_code"],
                                    historical_denial_rate=historical_denial_rate)
    score_result = pipeline_result["score_result"]
    explanation = pipeline_result["explanation"]
    extraction_result = pipeline_result["extraction_result"]
    fraud_flags = pipeline_result["fraud_flags"]
    reasons_payload = pipeline_result["reasons_payload"]

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO denial_scores (claim_id, risk_score, risk_level, reasons, policy_citations, model_version)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6)
                """,
                cid, score_result["risk_score"], score_result["risk_level"],
                reasons_payload, score_result["policy_citations"],
                score_result["model_version"],
            )
            await conn.execute(
                """
                INSERT INTO extracted_codings (note_id, icd10_codes, cpt_codes, missing_charges, model_used)
                VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5)
                """,
                note["id"],
                extraction_result["suggested_icd10_additions"],
                extraction_result["suggested_cpt_additions"],
                extraction_result["missing_charges"],
                extraction_result["model_used"],
            )
            for flag in fraud_flags:
                await conn.execute(
                    "INSERT INTO fraud_flags (claim_id, flag_type, severity, description) VALUES ($1, $2, $3, $4)",
                    cid, flag["flag_type"], flag["severity"], flag["description"],
                )

    await log_action(pool, user_id=None, action="score_claim", resource_type="claim",
                      resource_id=str(cid), phi_accessed=True,
                      details={"risk_level": score_result["risk_level"], "risk_score": score_result["risk_score"]})

    return {"score": score_result, "explanation": explanation, "extraction": extraction_result, "fraud_flags": fraud_flags}


@router.post("/{claim_id}/submit")
async def submit_claim(claim_id: str, pool=Depends(get_pool)):
    cid = _parse_uuid(claim_id)
    row = await pool.fetchrow(
        """
        UPDATE claims SET status = 'submitted', submitted_at = now()
        WHERE id = $1 AND status IN ('draft', 'ready')
        RETURNING id, status, submitted_at
        """,
        cid,
    )
    if row is None:
        raise HTTPException(status_code=409, detail="claim not in a submittable state")
    return row_to_dict(row)
