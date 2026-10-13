"""Batch-scores every claim already in Postgres, including historical
denied/paid claims - so the demo can show "our model would have caught this"
against real historical outcomes, not just the live 'ready' claims. Mirrors
the persistence logic in backend/app/routers/claims.py::run_scoring (the AI
computation itself is shared via ai/pipeline.py).

Safe to re-run: each run inserts a fresh denial_scores/extracted_codings row
per claim rather than upserting, and every reader queries "latest by
scored_at", so re-running just adds redundant history rather than corrupting
state - fine for a demo, not how you'd want a production backfill job to work.

Usage:
    python ingestion/score_all.py
"""
import asyncio
import json
import os
import pathlib
import sys

import asyncpg
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from ai.pipeline import run_pipeline  # noqa: E402


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://curasense:curasense@localhost:5432/curasense")
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def run():
    conn = await asyncpg.connect(_dsn())
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog", format="text")
    try:
        claims = await conn.fetch(
            """
            SELECT c.id, c.encounter_id, c.payer_id, c.icd10_codes, c.cpt_codes, pay.payer_code
            FROM claims c JOIN payers pay ON pay.id = c.payer_id
            """
        )
        scored = 0
        for claim_row in claims:
            claim = dict(claim_row)
            note = await conn.fetchrow(
                "SELECT id, content FROM clinical_notes WHERE encounter_id = $1 ORDER BY created_at LIMIT 1",
                claim["encounter_id"],
            )
            if note is None:
                continue

            historical_denial_rate = await conn.fetchval(
                """
                SELECT CASE WHEN count(*) FILTER (WHERE status IN ('denied', 'paid')) = 0 THEN NULL
                       ELSE count(*) FILTER (WHERE status = 'denied')::float
                            / count(*) FILTER (WHERE status IN ('denied', 'paid'))
                       END
                FROM claims WHERE payer_id = $1 AND id != $2
                """,
                claim["payer_id"], claim["id"],
            )

            result = run_pipeline(claim, note["content"], claim["payer_code"],
                                   historical_denial_rate=historical_denial_rate)

            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO denial_scores (claim_id, risk_score, risk_level, reasons, policy_citations, model_version)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6)
                    """,
                    claim["id"], result["score_result"]["risk_score"], result["score_result"]["risk_level"],
                    result["reasons_payload"], result["score_result"]["policy_citations"],
                    result["score_result"]["model_version"],
                )
                await conn.execute(
                    """
                    INSERT INTO extracted_codings (note_id, icd10_codes, cpt_codes, missing_charges, model_used)
                    VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5)
                    """,
                    note["id"],
                    result["extraction_result"]["suggested_icd10_additions"],
                    result["extraction_result"]["suggested_cpt_additions"],
                    result["extraction_result"]["missing_charges"],
                    result["extraction_result"]["model_used"],
                )
                for flag in result["fraud_flags"]:
                    await conn.execute(
                        "INSERT INTO fraud_flags (claim_id, flag_type, severity, description) VALUES ($1, $2, $3, $4)",
                        claim["id"], flag["flag_type"], flag["severity"], flag["description"],
                    )
            scored += 1
            print(f"scored claim {claim['id']}: {result['score_result']['risk_level']} ({result['score_result']['risk_score']})")
        print(f"\ndone: scored {scored} claims")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
