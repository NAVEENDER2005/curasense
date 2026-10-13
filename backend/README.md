# Backend (FastAPI)

Raw `asyncpg` (no ORM) for speed and transparency over a small schema - see
`db/migrations/0001_init.sql` for the source of truth. AI logic lives in
`ai/` (sibling of `backend/`) and is imported directly, not duplicated here.

## Run

From the repo root, once (creates the shared venv):

```bash
python -m venv .venv
.venv/Scripts/activate       # Windows
pip install -r backend/requirements.txt
```

Start Postgres, apply migrations, seed sample data, build the policy vector index:

```bash
docker compose up -d
python db/migrate.py
python ingestion/seed.py
python ai/build_index.py
```

Run the API (from the `backend/` directory, so `app.*` imports resolve as top-level):

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

`--reload` reliably watches `backend/` itself, but the AI logic lives in the
sibling `ai/` package, and cross-directory watching via `--reload-dir ../ai`
was flaky in testing (edits there sometimes weren't picked up even after the
reloader logged a reload). **If you edit anything under `ai/`, restart the
server manually** rather than trusting the auto-reload for it.

Docs at `http://localhost:8000/docs`.

## Auth note

There's no login system in this build (out of scope for the demo). Requests
carry an `X-User-Role` header (`billing_staff` | `cfo` | `compliance` | `admin`)
read by `app/dependencies.py`; every PHI-touching read/write is still
audit-logged (`app/audit.py`) regardless of role, to demonstrate the RBAC +
audit-trail pattern a production build would enforce via real sessions/JWTs.
