"""Loads the mock HL7/FHIR-style sample data into Postgres.

Real integrations would replace `sample_data/fhir_bundle.json` with live reads
from an Epic or Cerner FHIR R4 endpoint (Patient, Encounter, DocumentReference,
Claim resources) - see README.md in this directory for the swap-in points.

Usage:
    python ingestion/seed.py
"""
import asyncio
import json
import os
import pathlib
from datetime import date, datetime

import asyncpg
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DATA_DIR = pathlib.Path(__file__).resolve().parent / "sample_data"


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://curasense:curasense@localhost:5432/curasense")
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _by_type(entries, resource_type):
    return [e["resource"] for e in entries if e["resource"]["resourceType"] == resource_type]


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


async def seed_payers(conn, payers: list[dict]) -> dict[str, str]:
    code_to_id = {}
    for p in payers:
        row = await conn.fetchrow(
            """
            INSERT INTO payers (name, payer_code) VALUES ($1, $2)
            ON CONFLICT (payer_code) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            p["name"], p["payer_code"],
        )
        code_to_id[p["payer_code"]] = row["id"]
    return code_to_id


async def seed_clinical_data(conn, entries: list[dict], payer_code_to_id: dict[str, str]):
    patients = _by_type(entries, "Patient")
    encounters = _by_type(entries, "Encounter")
    notes = _by_type(entries, "DocumentReference")
    claims = _by_type(entries, "Claim")

    patient_ref_to_id: dict[str, str] = {}
    for p in patients:
        given = " ".join(p["name"][0].get("given", []))
        family = p["name"][0]["family"]
        payer_id = payer_code_to_id.get(p.get("curasensePayerCode"))
        row = await conn.fetchrow(
            """
            INSERT INTO patients (mrn, first_name, last_name, date_of_birth, gender, payer_id, member_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (mrn) DO UPDATE SET first_name = EXCLUDED.first_name
            RETURNING id
            """,
            p["identifier"][0]["value"], given, family, _parse_date(p["birthDate"]), p.get("gender"),
            payer_id, p.get("curasenseMemberId"),
        )
        patient_ref_to_id[p["id"]] = row["id"]

    encounter_ref_to_id: dict[str, str] = {}
    for e in encounters:
        row = await conn.fetchrow(
            """
            INSERT INTO encounters (patient_id, fhir_encounter_id, encounter_type, department, attending_physician, admit_date, discharge_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (fhir_encounter_id) DO UPDATE SET department = EXCLUDED.department
            RETURNING id
            """,
            patient_ref_to_id[e["patientRef"]], e["id"], e["class"], e.get("serviceType"),
            e.get("attendingPhysician"), _parse_datetime(e["period"]["start"]), _parse_datetime(e["period"].get("end")),
        )
        encounter_ref_to_id[e["id"]] = row["id"]

    note_ref_to_id: dict[str, str] = {}
    for n in notes:
        row = await conn.fetchrow(
            """
            INSERT INTO clinical_notes (encounter_id, note_type, author, content, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            encounter_ref_to_id[n["encounterRef"]], n["type"], n.get("author"),
            n["contentPlainText"], _parse_datetime(n["date"]),
        )
        note_ref_to_id[n["id"]] = row["id"]

    for c in claims:
        await conn.execute(
            """
            INSERT INTO claims (
                claim_number, encounter_id, payer_id, icd10_codes, cpt_codes,
                total_billed, status, denial_reason, submitted_at, decided_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (claim_number) DO NOTHING
            """,
            c["claimNumber"], encounter_ref_to_id[c["encounterRef"]],
            payer_code_to_id[c["payerCode"]],
            json.dumps(c["diagnosisCodes"]), json.dumps(c["procedureCodes"]),
            c["totalBilled"], c["curasenseStatus"], c.get("curasenseDenialReason"),
            _parse_datetime(c.get("curasenseSubmittedAt")), _parse_datetime(c.get("curasenseDecidedAt")),
        )

    return note_ref_to_id


async def seed_policies(conn, policies: list[dict], payer_code_to_id: dict[str, str]):
    for pol in policies:
        await conn.execute(
            """
            INSERT INTO payer_policies (payer_id, policy_number, title, category, content, effective_date)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (payer_id, policy_number) DO UPDATE SET content = EXCLUDED.content
            """,
            payer_code_to_id[pol["payer_code"]], pol["policy_number"], pol["title"],
            pol.get("category"), pol["content"], _parse_date(pol.get("effective_date")),
        )


async def run():
    payers = json.loads((DATA_DIR / "payers.json").read_text(encoding="utf-8"))
    bundle = json.loads((DATA_DIR / "fhir_bundle.json").read_text(encoding="utf-8"))
    policies = json.loads((DATA_DIR / "payer_policies.json").read_text(encoding="utf-8"))

    conn = await asyncpg.connect(_dsn())
    try:
        payer_code_to_id = await seed_payers(conn, payers)
        await seed_clinical_data(conn, bundle["entry"], payer_code_to_id)
        await seed_policies(conn, policies, payer_code_to_id)
        n_claims = await conn.fetchval("SELECT count(*) FROM claims")
        n_policies = await conn.fetchval("SELECT count(*) FROM payer_policies")
        print(f"seeded: {n_claims} claims, {n_policies} payer policies")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
