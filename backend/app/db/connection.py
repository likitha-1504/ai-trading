"""Database connection management with SQLite WAL and safe transaction handling."""

import os
import sqlite3
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

import aiosqlite

from app.core.config import settings
from app.db.schema import DDL_STATEMENTS


def get_db_path(db_path: str | None = None) -> str:
    """Resolve database path from argument, environment, or settings."""
    if db_path is not None:
        return db_path
    return getattr(settings, "DATABASE_PATH", "trading_agent.db")


def init_db(db_path: str | None = None) -> None:
    """Initialize database tables, foreign keys, and WAL pragma synchronously."""
    path = get_db_path(db_path)
    if path != ":memory:":
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)

    with sqlite3.connect(path, timeout=5.0) as conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.executescript(DDL_STATEMENTS)
        conn.commit()


@contextmanager
def get_connection(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Safe synchronous transaction context manager with WAL and foreign key enforcement."""
    path = get_db_path(db_path)
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@asynccontextmanager
async def get_async_connection(
    db_path: str | None = None,
) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Safe asynchronous transaction context manager with WAL mode enabled."""
    path = get_db_path(db_path)
    db = await aiosqlite.connect(path, timeout=5.0)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode = WAL;")
    await db.execute("PRAGMA synchronous = NORMAL;")
    await db.execute("PRAGMA foreign_keys = ON;")
    await db.execute("PRAGMA busy_timeout = 5000;")
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()
