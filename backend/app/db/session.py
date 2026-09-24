"""SQLite WAL database connection management."""

import aiosqlite

from app.core.config import settings
from app.db.connection import get_async_connection, get_connection, get_db_path, init_db


async def get_db_connection() -> aiosqlite.Connection:
    """Yield an aiosqlite connection with WAL mode enabled (legacy/fastapi compatibility)."""
    db = await aiosqlite.connect(settings.DATABASE_PATH, timeout=5.0)
    await db.execute("PRAGMA journal_mode = WAL;")
    await db.execute("PRAGMA synchronous = NORMAL;")
    await db.execute("PRAGMA foreign_keys = ON;")
    await db.execute("PRAGMA busy_timeout = 5000;")
    db.row_factory = aiosqlite.Row
    return db


__all__ = [
    "get_async_connection",
    "get_connection",
    "get_db_connection",
    "get_db_path",
    "init_db",
]
