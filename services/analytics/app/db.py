"""Database connection and utilities."""

import asyncio
from contextlib import asynccontextmanager

from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.settings import settings

_pool: AsyncConnectionPool | None = None
_pool_lock = asyncio.Lock()


def _build_pool() -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
        timeout=30,
        kwargs={
            "row_factory": dict_row,
            "autocommit": False,
        },
        open=False,
    )


async def init_db_pool() -> None:
    """Initialize the shared async connection pool."""
    global _pool

    if _pool is not None and not _pool.closed:
        return

    async with _pool_lock:
        if _pool is not None and not _pool.closed:
            return
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not set")

        _pool = _build_pool()
        # Avoid blocking startup on initial pool fill; connections are established lazily.
        await _pool.open(wait=False)


async def close_db_pool() -> None:
    """Close the shared async connection pool."""
    global _pool
    if _pool is None:
        return
    if not _pool.closed:
        await _pool.close()
    _pool = None


async def _get_pool() -> AsyncConnectionPool:
    if _pool is None or _pool.closed:
        await init_db_pool()
    assert _pool is not None
    return _pool


@asynccontextmanager
async def get_db_system():
    """Context manager for system-level database operations.

    Used for pre-auth operations: register, login, session validation,
    cleanup, migrations. No RLS context is set.
    """
    pool = await _get_pool()
    async with pool.connection() as conn:
        yield conn


@asynccontextmanager
async def get_db_for_user(user_id: str):
    """Context manager for user-scoped database operations.

    Sets SET LOCAL app.current_user_id for RLS enforcement.
    The connection stays in a single transaction for the entire request.

    Args:
        user_id: UUID string of the authenticated user
    """
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            await conn.execute(
                sql.SQL("SET LOCAL app.current_user_id = {}").format(
                    sql.Literal(str(user_id))
                )
            )
            yield conn


# Legacy alias — banned in request handlers (use get_db_for_user or get_db_system)
@asynccontextmanager
async def get_db():
    """Legacy context manager. Do not use in request handlers."""
    pool = await _get_pool()
    async with pool.connection() as conn:
        yield conn
