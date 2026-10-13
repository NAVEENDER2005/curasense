# CuraSense AI

Intelligent healthcare Revenue Cycle Management (RCM) platform: predicts and
prevents claim denials, auto-drafts appeal letters, cross-references claims
against payer policy in real time, and flags compliance risk - all before a
claim ever reaches the payer.

**All data in this repo is synthetic** (`ingestion/sample_data/`). No real
patient data, no real EHR credentials, no real payer connections.

## What's here

| Layer | Directory | Stack |
|---|---|---|
| Frontend | `frontend/` | Next.js (App Router) + TypeScript + Tailwind v4 |
| Backend API | `backend/` | FastAPI + raw `asyncpg` (no ORM) |
| Database | `db/` | PostgreSQL, plain-SQL migrations |
| Mock EHR ingestion | `ingestion/` | Synthetic FHIR-shaped Patient/Encounter/DocumentReference/Claim bundle |
| AI Intelligence Hub | `ai/` | Denial scoring, RAG policy validation, auto-coding, appeals, fraud detection, Ask My Data |

See each directory's own README for details. `ai/README.md` in particular
explains the design choices (why scoring is a transparent rule engine, why
"Ask My Data" never runs LLM-generated SQL, how everything degrades to a
fully offline mock mode with zero API keys).

## Quickstart

Requires: Python 3.11+, Node 18+, and a Postgres instance (Docker recommended).

```bash
# 1. Start Postgres
docker compose up -d

# 2. Python side (repo root)
python -m venv .venv
.venv/Scripts/activate          # Windows; use .venv/bin/activate on macOS/Linux
pip install -r backend/requirements.txt
cp .env.example .env            # defaults already match docker-compose

# 3. Load schema + mock data + AI setup
python db/migrate.py
python ingestion/seed.py
python ai/build_index.py
python ingestion/score_all.py   # pre-scores every claim, incl. historical ones

# 4. Backend (from backend/, so `app.*` imports resolve)
cd backend
python -m uvicorn app.main:app --reload --port 8000
# docs at http://localhost:8000/docs

# 5. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# app at http://localhost:3000
```

No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `PINECONE_API_KEY` needed to run
the full demo - see `ai/README.md` for what upgrades when you add them.

## The demo flow

1. **Revenue Command Center** (`/dashboard`) - revenue-at-risk, denial rate,
   denials by payer, recent denials.
2. **Provider Workflow** (`/claims`) - only high-risk pending claims are shown
   by default (the noise-reduction principle from the spec); toggle to see
   everything.
3. **Claim Deep-Dive** (`/claims/[id]`) - split screen: the original claim
   file next to the AI's denial explanation, coding suggestions, and
   compliance flags. "Run AI Analysis" triggers the live scoring pipeline.
4. **Appeals Hub** (`/appeals`) - denied claims get an auto-drafted,
   policy-cited appeal letter on demand.
5. **Policy Intelligence** (`/policies`) - browse payer policies, or run a
   RAG search over them directly.
6. **Ask My Data** (`/ask`) - chat over the revenue aggregates above.

The seeded data is built so the model *retrodicts* three real historical
denials correctly (matching the actual payer-stated denial reason) and
predicts a fourth, not-yet-submitted claim as high risk before it ever ships -
run `ingestion/score_all.py` and compare `denial_scores` against
`claims.denial_reason` to see this directly.

## Known simplifications (by design, for this build)

- **Auth is a header, not a login system** (`X-User-Role`) - see
  `backend/README.md`. Every PHI-touching request is still audit-logged.
- **LangChain / LlamaIndex are listed in `backend/requirements.txt` but not
  used by the running code.** The AI layer (`ai/llm.py`, `ai/rag.py`) is a
  small, dependency-light implementation of the same ideas (prompt
  orchestration, retrieval) so the whole app runs offline with zero API keys.
  The interfaces are narrow enough to swap in LangChain/LlamaIndex later
  without touching callers.
- **Historical denial-rate signal is noisy at this data scale** (a handful of
  claims per payer) - see the comment in `ai/scoring.py`. It's a real,
  legitimate signal, just amplified by small N in the seed data.
- **No real HL7/FHIR connection.** `ingestion/README.md` documents exactly
  where a real Epic/Cerner FHIR feed would plug in.

## Compliance & security posture

Designed HIPAA-aware even though every record here is synthetic: role-based
access control at the API boundary, full audit trail (`audit_logs`, never
containing PHI content) on every claim/appeal read or write, and explicit
`COMPLIANCE NOTE` comments in `ai/` at every point clinical text would leave
the process for a third-party LLM call (requires a signed BAA in production -
see `ai/README.md`).
