-- CuraSense AI - initial schema
-- All patient data in this schema is synthetic (see ingestion/). Design still
-- follows PHI-handling conventions: no free-text PHI in audit_logs, and every
-- table that could hold PHI is access-controlled via the backend's RBAC layer,
-- not exposed directly.

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('billing_staff', 'cfo', 'compliance', 'admin')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    payer_code      TEXT UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS patients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mrn             TEXT UNIQUE NOT NULL,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    date_of_birth   DATE NOT NULL,
    gender          TEXT,
    payer_id        UUID REFERENCES payers(id),
    member_id       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS encounters (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    fhir_encounter_id   TEXT UNIQUE,
    encounter_type      TEXT NOT NULL,
    department          TEXT,
    attending_physician TEXT,
    admit_date          TIMESTAMPTZ NOT NULL,
    discharge_date      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_encounters_patient ON encounters(patient_id);

CREATE TABLE IF NOT EXISTS clinical_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id    UUID NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
    note_type       TEXT NOT NULL CHECK (note_type IN ('physician_note', 'discharge_summary', 'progress_note')),
    author          TEXT,
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notes_encounter ON clinical_notes(encounter_id);

CREATE TABLE IF NOT EXISTS extracted_codings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id         UUID NOT NULL REFERENCES clinical_notes(id) ON DELETE CASCADE,
    icd10_codes     JSONB NOT NULL DEFAULT '[]',
    cpt_codes       JSONB NOT NULL DEFAULT '[]',
    missing_charges JSONB NOT NULL DEFAULT '[]',
    model_used      TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_codings_note ON extracted_codings(note_id);

CREATE TABLE IF NOT EXISTS claims (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_number    TEXT UNIQUE NOT NULL,
    encounter_id    UUID NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
    payer_id        UUID NOT NULL REFERENCES payers(id),
    icd10_codes     JSONB NOT NULL DEFAULT '[]',
    cpt_codes       JSONB NOT NULL DEFAULT '[]',
    total_billed    NUMERIC(12, 2) NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'ready', 'submitted', 'paid', 'denied', 'appealed', 'recovered')),
    denial_reason   TEXT,
    submitted_at    TIMESTAMPTZ,
    decided_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_claims_encounter ON claims(encounter_id);
CREATE INDEX IF NOT EXISTS idx_claims_payer ON claims(payer_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);

CREATE TABLE IF NOT EXISTS payer_policies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payer_id        UUID NOT NULL REFERENCES payers(id) ON DELETE CASCADE,
    policy_number   TEXT NOT NULL,
    title           TEXT NOT NULL,
    category        TEXT,
    content         TEXT NOT NULL,
    effective_date  DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (payer_id, policy_number)
);

CREATE TABLE IF NOT EXISTS denial_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    risk_score      NUMERIC(5, 2) NOT NULL,
    risk_level      TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
    reasons         JSONB NOT NULL DEFAULT '[]',
    policy_citations JSONB NOT NULL DEFAULT '[]',
    model_version   TEXT NOT NULL,
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_denial_scores_claim ON denial_scores(claim_id);

CREATE TABLE IF NOT EXISTS appeal_letters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    denial_reason   TEXT,
    letter_content  TEXT NOT NULL,
    evidence_used   JSONB NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'reviewed', 'sent')),
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_appeals_claim ON appeal_letters(claim_id);

CREATE TABLE IF NOT EXISTS fraud_flags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    flag_type       TEXT NOT NULL CHECK (flag_type IN ('upcoding', 'unbundling', 'frequency_anomaly', 'duplicate_billing')),
    severity        TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    description     TEXT NOT NULL,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fraud_flags_claim ON fraud_flags(claim_id);

-- No free-text PHI here by design: only resource ids/types and non-PHI metadata.
CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     UUID,
    phi_accessed    BOOLEAN NOT NULL DEFAULT false,
    details         JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
