"""Builds the RAG vector index from payer_policies rows already in Postgres.

Usage:
    python ai/build_index.py
"""
import asyncio
import os
import pathlib
import sys

import asyncpg
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from ai.rag import index_policies  # noqa: E402


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://curasense:curasense@localhost:5432/curasense")
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def run():
    conn = await asyncpg.connect(_dsn())
    try:
        rows = await conn.fetch(
            """
            SELECT pp.id, pay.payer_code, pp.policy_number, pp.title, pp.category, pp.content
            FROM payer_policies pp
            JOIN payers pay ON pay.id = pp.payer_id
            """
        )
    finally:
        await conn.close()

    policies = [dict(r) for r in rows]
    for p in policies:
        p["id"] = str(p["id"])
    n = index_policies(policies)
    print(f"indexed {n} payer policies into the vector store")


if __name__ == "__main__":
    asyncio.run(run())
