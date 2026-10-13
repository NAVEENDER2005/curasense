"""Batch scores all claims into SQLite."""
import json
import pathlib
import sqlite3
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.pipeline import run_pipeline

DB_PATH = ROOT / "curasense.db"

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def seed_scores():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    claims = cursor.execute("""
        SELECT c.id, c.encounter_id, c.payer_id, c.icd10_codes, c.cpt_codes, c.total_billed, pay.payer_code
        FROM claims c JOIN payers pay ON pay.id = c.payer_id
    """).fetchall()

    for claim in claims:
        if isinstance(claim["icd10_codes"], str):
            claim["icd10_codes"] = json.loads(claim["icd10_codes"])
        if isinstance(claim["cpt_codes"], str):
            claim["cpt_codes"] = json.loads(claim["cpt_codes"])

        note = cursor.execute("SELECT id, content FROM clinical_notes WHERE encounter_id = ? ORDER BY created_at LIMIT 1", (claim["encounter_id"],)).fetchone()
        if not note:
            continue

        result = run_pipeline(claim, note["content"], claim["payer_code"], historical_denial_rate=0.25)
        score_res = result["score_result"]
        ext_res = result["extraction_result"]

        score_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO denial_scores (id, claim_id, risk_score, risk_level, reasons, policy_citations, model_version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (score_id, claim["id"], score_res["risk_score"], score_res["risk_level"], json.dumps(result["reasons_payload"]), json.dumps(score_res["policy_citations"]), score_res["model_version"]))

        ext_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO extracted_codings (id, note_id, icd10_codes, cpt_codes, missing_charges, model_used)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ext_id, note["id"], json.dumps(ext_res["suggested_icd10_additions"]), json.dumps(ext_res["suggested_cpt_additions"]), json.dumps(ext_res["missing_charges"]), ext_res["model_used"]))

        for flag in result["fraud_flags"]:
            flag_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO fraud_flags (id, claim_id, flag_type, severity, description) VALUES (?, ?, ?, ?, ?)",
                           (flag_id, claim["id"], flag["flag_type"], flag["severity"], flag["description"]))

    conn.commit()
    conn.close()
    print("Scored all claims in SQLite successfully!")

if __name__ == "__main__":
    seed_scores()
