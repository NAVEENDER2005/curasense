import json
import sqlite3

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class MockPool:
    def __init__(self, db_path=":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = dict_factory
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS payers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                payer_code TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                mrn TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                gender TEXT,
                payer_id TEXT,
                member_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS encounters (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                fhir_encounter_id TEXT UNIQUE,
                encounter_type TEXT NOT NULL,
                department TEXT,
                attending_physician TEXT,
                admit_date TEXT NOT NULL,
                discharge_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS clinical_notes (
                id TEXT PRIMARY KEY,
                encounter_id TEXT NOT NULL,
                note_type TEXT NOT NULL,
                author TEXT,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS extracted_codings (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                icd10_codes TEXT NOT NULL DEFAULT '[]',
                cpt_codes TEXT NOT NULL DEFAULT '[]',
                missing_charges TEXT NOT NULL DEFAULT '[]',
                model_used TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                claim_number TEXT UNIQUE NOT NULL,
                encounter_id TEXT NOT NULL,
                payer_id TEXT NOT NULL,
                icd10_codes TEXT NOT NULL DEFAULT '[]',
                cpt_codes TEXT NOT NULL DEFAULT '[]',
                total_billed REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                denial_reason TEXT,
                submitted_at TEXT,
                decided_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS payer_policies (
                id TEXT PRIMARY KEY,
                payer_id TEXT NOT NULL,
                policy_number TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT,
                content TEXT NOT NULL,
                effective_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS denial_scores (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                reasons TEXT NOT NULL DEFAULT '[]',
                policy_citations TEXT NOT NULL DEFAULT '[]',
                model_version TEXT NOT NULL,
                scored_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS appeal_letters (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                denial_reason TEXT,
                letter_content TEXT NOT NULL,
                evidence_used TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'draft',
                generated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS fraud_flags (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                flag_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
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

    async def fetch(self, query: str, *args):
        formatted_query, formatted_args = self._convert_query(query, args)
        cursor = self.conn.cursor()
        cursor.execute(formatted_query, formatted_args)
        rows = cursor.fetchall()
        return [self._decode_row(r) for r in rows]

    async def fetchrow(self, query: str, *args):
        rows = await self.fetch(query, *args)
        return rows[0] if rows else None

    async def fetchval(self, query: str, *args):
        row = await self.fetchrow(query, *args)
        if row:
            return list(row.values())[0]
        return None

    async def execute(self, query: str, *args):
        formatted_query, formatted_args = self._convert_query(query, args)
        cursor = self.conn.cursor()
        cursor.execute(formatted_query, formatted_args)
        self.conn.commit()
        return cursor.rowcount

    def _convert_query(self, query: str, args):
        import re
        q = re.sub(r'::[a-zA-Z0-9_]+', '', query)
        
        import json, uuid
        def _fix_arg(a):
            if isinstance(a, uuid.UUID):
                return str(a)
            if isinstance(a, (dict, list)):
                return json.dumps(a)
            return a

        # Find parameter indices like $1, $2
        param_indices = [int(m) - 1 for m in re.findall(r'\$(\d+)', q)]
        if param_indices and args:
            new_args = tuple(_fix_arg(args[i]) for i in param_indices if i < len(args))
        else:
            new_args = tuple(_fix_arg(a) for a in args)

        q = re.sub(r'\$\d+', '?', q)
        q = q.replace('now()', 'CURRENT_TIMESTAMP')
        # Translate JOIN LATERAL (SELECT ... LIMIT 1) ds ON true to SQLite compatible subqueries
        if "JOIN LATERAL" in q:
            q = re.sub(
                r"JOIN LATERAL \(\s*SELECT risk_level FROM denial_scores WHERE claim_id = c\.id ORDER BY scored_at DESC LIMIT 1\s*\) ds ON true",
                "LEFT JOIN (SELECT claim_id, risk_level FROM denial_scores GROUP BY claim_id HAVING scored_at = MAX(scored_at)) ds ON ds.claim_id = c.id",
                q, flags=re.IGNORECASE | re.DOTALL
            )
            q = re.sub(
                r"LEFT JOIN LATERAL \(\s*SELECT risk_score, risk_level, scored_at FROM denial_scores\s*WHERE claim_id = c\.id ORDER BY scored_at DESC LIMIT 1\s*\) ds ON true",
                "LEFT JOIN (SELECT claim_id, risk_score, risk_level, scored_at FROM denial_scores GROUP BY claim_id HAVING scored_at = MAX(scored_at)) ds ON ds.claim_id = c.id",
                q, flags=re.IGNORECASE | re.DOTALL
            )
            q = re.sub(
                r"LEFT JOIN LATERAL \(\s*SELECT id, status, generated_at FROM appeal_letters WHERE claim_id = c\.id ORDER BY generated_at DESC LIMIT 1\s*\) al ON true",
                "LEFT JOIN (SELECT claim_id, id, status, generated_at FROM appeal_letters GROUP BY claim_id HAVING generated_at = MAX(generated_at)) al ON al.claim_id = c.id",
                q, flags=re.IGNORECASE | re.DOTALL
            )
        # Convert Postgres FILTER syntax for SQLite
        if "FILTER" in q:
            q = re.sub(r"COALESCE\(sum\(([^)]+)\)\s*FILTER\s*\(\s*WHERE\s*(.*?)\)\s*,\s*0\)", r"COALESCE(sum(CASE WHEN \2 THEN \1 ELSE 0 END), 0)", q, flags=re.IGNORECASE)
            q = re.sub(r"sum\(([^)]+)\)\s*FILTER\s*\(\s*WHERE\s*(.*?)\)", r"sum(CASE WHEN \2 THEN \1 ELSE 0 END)", q, flags=re.IGNORECASE)
            q = re.sub(r"count\(\*\)\s*FILTER\s*\(\s*WHERE\s*(\b[^)]*?\b|\bstatus IN \([^)]+\)\b)\)", r"count(CASE WHEN \1 THEN 1 END)", q, flags=re.IGNORECASE)
            # direct exact string replacements for analytics query
            q = q.replace("count(*) FILTER (WHERE status = 'denied')", "count(CASE WHEN status = 'denied' THEN 1 END)")
            q = q.replace("count(*) FILTER (WHERE status IN ('denied', 'paid'))", "count(CASE WHEN status IN ('denied', 'paid') THEN 1 END)")
            q = q.replace("count(*) FILTER (WHERE status = 'ready')", "count(CASE WHEN status = 'ready' THEN 1 END)")
            q = q.replace("count(*) FILTER (WHERE status = 'recovered')", "count(CASE WHEN status = 'recovered' THEN 1 END)")
            q = q.replace("COALESCE(sum(total_billed) FILTER (WHERE status = 'denied'), 0)", "COALESCE(sum(CASE WHEN status = 'denied' THEN total_billed ELSE 0 END), 0)")
        return q, new_args

    def _decode_row(self, row: dict) -> dict:
        decoded = {}
        for k, v in row.items():
            if isinstance(v, str) and (v.startswith('[') or v.startswith('{')):
                try:
                    decoded[k] = json.loads(v)
                    continue
                except json.JSONDecodeError:
                    pass
            decoded[k] = v
        return decoded

    def acquire(self):
        class ConnectionContext:
            def __init__(ctx, pool):
                ctx.pool = pool
            async def __aenter__(ctx):
                return ctx.pool
            async def __aexit__(ctx, exc_type, exc, tb):
                pass
        return ConnectionContext(self)

    def transaction(self):
        class TransactionContext:
            async def __aenter__(ctx):
                pass
            async def __aexit__(ctx, exc_type, exc, tb):
                pass
        return TransactionContext()

    async def close(self):
        self.conn.close()

