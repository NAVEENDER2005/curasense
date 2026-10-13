"""SQLite Seeder for zero-external-dependency E2E local running."""
import json
import pathlib
import sqlite3
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "ingestion" / "sample_data"
DB_PATH = ROOT / "curasense.db"

def seed():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE payers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            payer_code TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE patients (
            id TEXT PRIMARY KEY,
            mrn TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            gender TEXT,
            payer_id TEXT REFERENCES payers(id),
            member_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE encounters (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(id),
            fhir_encounter_id TEXT UNIQUE,
            encounter_type TEXT NOT NULL,
            department TEXT,
            attending_physician TEXT,
            admit_date TEXT NOT NULL,
            discharge_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE clinical_notes (
            id TEXT PRIMARY KEY,
            encounter_id TEXT NOT NULL REFERENCES encounters(id),
            note_type TEXT NOT NULL,
            author TEXT,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE extracted_codings (
            id TEXT PRIMARY KEY,
            note_id TEXT NOT NULL REFERENCES clinical_notes(id),
            icd10_codes TEXT NOT NULL DEFAULT '[]',
            cpt_codes TEXT NOT NULL DEFAULT '[]',
            missing_charges TEXT NOT NULL DEFAULT '[]',
            model_used TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE claims (
            id TEXT PRIMARY KEY,
            claim_number TEXT UNIQUE NOT NULL,
            encounter_id TEXT NOT NULL REFERENCES encounters(id),
            payer_id TEXT NOT NULL REFERENCES payers(id),
            icd10_codes TEXT NOT NULL DEFAULT '[]',
            cpt_codes TEXT NOT NULL DEFAULT '[]',
            total_billed REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            denial_reason TEXT,
            submitted_at TEXT,
            decided_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE payer_policies (
            id TEXT PRIMARY KEY,
            payer_id TEXT NOT NULL REFERENCES payers(id),
            policy_number TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT,
            content TEXT NOT NULL,
            effective_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(payer_id, policy_number)
        );
        CREATE TABLE denial_scores (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL REFERENCES claims(id),
            risk_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            reasons TEXT NOT NULL DEFAULT '[]',
            policy_citations TEXT NOT NULL DEFAULT '[]',
            model_version TEXT NOT NULL,
            scored_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE appeal_letters (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL REFERENCES claims(id),
            denial_reason TEXT,
            letter_content TEXT NOT NULL,
            evidence_used TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'draft',
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE fraud_flags (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL REFERENCES claims(id),
            flag_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            detected_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            phi_accessed INTEGER NOT NULL DEFAULT 0,
            details TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    payers = json.loads((DATA_DIR / "payers.json").read_text(encoding="utf-8"))
    bundle = json.loads((DATA_DIR / "fhir_bundle.json").read_text(encoding="utf-8"))
    policies = json.loads((DATA_DIR / "payer_policies.json").read_text(encoding="utf-8"))

    payer_code_to_id = {}
    for p in payers:
        pid = str(uuid.uuid4())
        cursor.execute("INSERT INTO payers (id, name, payer_code) VALUES (?, ?, ?)", (pid, p["name"], p["payer_code"]))
        payer_code_to_id[p["payer_code"]] = pid

    entries = bundle["entry"]
    patients = [e["resource"] for e in entries if e["resource"]["resourceType"] == "Patient"]
    encounters = [e["resource"] for e in entries if e["resource"]["resourceType"] == "Encounter"]
    notes = [e["resource"] for e in entries if e["resource"]["resourceType"] == "DocumentReference"]
    claims = [e["resource"] for e in entries if e["resource"]["resourceType"] == "Claim"]

    patient_ref_to_id = {}
    for p in patients:
        pid = str(uuid.uuid4())
        given = " ".join(p["name"][0].get("given", []))
        family = p["name"][0]["family"]
        payer_id = payer_code_to_id.get(p.get("curasensePayerCode"))
        cursor.execute(
            "INSERT INTO patients (id, mrn, first_name, last_name, date_of_birth, gender, payer_id, member_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, p["identifier"][0]["value"], given, family, p["birthDate"], p.get("gender"), payer_id, p.get("curasenseMemberId"))
        )
        patient_ref_to_id[p["id"]] = pid

    encounter_ref_to_id = {}
    for e in encounters:
        eid = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO encounters (id, patient_id, fhir_encounter_id, encounter_type, department, attending_physician, admit_date, discharge_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (eid, patient_ref_to_id[e["patientRef"]], e["id"], e["class"], e.get("serviceType"), e.get("attendingPhysician"), e["period"]["start"], e["period"].get("end"))
        )
        encounter_ref_to_id[e["id"]] = eid

    for n in notes:
        nid = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO clinical_notes (id, encounter_id, note_type, author, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (nid, encounter_ref_to_id[n["encounterRef"]], n["type"], n.get("author"), n["contentPlainText"], n["date"])
        )

    for c in claims:
        cid = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO claims (id, claim_number, encounter_id, payer_id, icd10_codes, cpt_codes, total_billed, status, denial_reason, submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, c["claimNumber"], encounter_ref_to_id[c["encounterRef"]], payer_code_to_id[c["payerCode"]], json.dumps(c["diagnosisCodes"]), json.dumps(c["procedureCodes"]), c["totalBilled"], c["curasenseStatus"], c.get("curasenseDenialReason"), c.get("curasenseSubmittedAt"), c.get("curasenseDecidedAt"))
        )

    for pol in policies:
        pol_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO payer_policies (id, payer_id, policy_number, title, category, content, effective_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pol_id, payer_code_to_id[pol["payer_code"]], pol["policy_number"], pol["title"], pol.get("category"), pol["content"], pol.get("effective_date"))
        )

    conn.commit()
    conn.close()
    print("SQLite seeded successfully!")

if __name__ == "__main__":
    seed()
