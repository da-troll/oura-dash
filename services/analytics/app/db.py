"""Database connection and utilities."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import psycopg
from psycopg.rows import dict_row

from app.settings import settings


async def get_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """Get an async database connection."""
    async with await psycopg.AsyncConnection.connect(
        settings.database_url,
        row_factory=dict_row,
    ) as conn:
        yield conn


@asynccontextmanager
async def get_db():
    """Context manager for database connection."""
    async with await psycopg.AsyncConnection.connect(
        settings.database_url,
        row_factory=dict_row,
    ) as conn:
        yield conn


async def execute_sql(sql: str, params: tuple | None = None) -> list[dict]:
    """Execute SQL and return results as list of dicts."""
    async with get_db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            if cur.description:
                return await cur.fetchall()
            return []


async def execute_sql_single(sql: str, params: tuple | None = None) -> dict | None:
    """Execute SQL and return single result as dict."""
    results = await execute_sql(sql, params)
    return results[0] if results else None


async def execute_sql_write(sql: str, params: tuple | None = None) -> None:
    """Execute SQL write operation (INSERT/UPDATE/DELETE)."""
    async with get_db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
        await conn.commit()
