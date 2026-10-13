"""Tiny migration runner: applies db/migrations/*.sql in order, once each.

Usage:
    python db/migrate.py

Tracks applied migrations in a `schema_migrations` table so re-running is safe.
"""
import asyncio
import os
import pathlib

import asyncpg
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent / "migrations"


def _to_asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def run():
    dsn = _to_asyncpg_dsn(os.environ.get("DATABASE_URL", "postgresql://curasense:curasense@localhost:5432/curasense"))
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        applied = {row["filename"] for row in await conn.fetch("SELECT filename FROM schema_migrations")}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                print(f"skip  {path.name} (already applied)")
                continue
            print(f"apply {path.name}")
            sql = path.read_text(encoding="utf-8")
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)", path.name
                )
        print("migrations up to date")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
