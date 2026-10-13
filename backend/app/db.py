import json
import os

import asyncpg


def dsn() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://curasense:curasense@localhost:5432/curasense")
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _init_connection(conn: asyncpg.Connection) -> None:
    # jsonb columns come back as parsed dict/list instead of raw JSON text
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog", format="text")


async def create_pool():
    try:
        pool = await asyncpg.create_pool(dsn(), min_size=1, max_size=10, init=_init_connection)
        return pool
    except Exception as exc:
        try:
            from app.sqlite_fallback import MockPool
        except ImportError:
            from backend.app.sqlite_fallback import MockPool
        import pathlib
        db_path = str(pathlib.Path(__file__).resolve().parent.parent.parent / "curasense.db")
        return MockPool(db_path)


def row_to_dict(row: asyncpg.Record | dict | None) -> dict | None:
    if row is None:
        return None
    return dict(row) if isinstance(row, (asyncpg.Record, dict)) else row


def rows_to_list(rows: list[asyncpg.Record | dict]) -> list[dict]:
    return [dict(r) for r in rows]

