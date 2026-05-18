"""Database connection pool and initialization using asyncpg."""

import asyncpg
import os
from pathlib import Path

from app.config import get_settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _pool


async def init_db() -> asyncpg.Pool:
    """Initialize the connection pool and run schema migration."""
    global _pool
    settings = get_settings()

    # Parse the DATABASE_URL for asyncpg (it uses keyword args, not URL by default)
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
    )

    # Run schema.sql
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    async with _pool.acquire() as conn:
        await conn.execute(schema_sql)

    print(f"[DB] Schema applied. Connected to {settings.database_url.split('@')[1]}")
    return _pool


async def close_db():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        print("[DB] Connection pool closed.")
