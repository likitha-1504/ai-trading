"""SQLite WAL database connection management scaffold."""

import aiosqlite
from app.core.config import settings


async def get_db_connection():
    """Yield an aiosqlite connection with WAL mode enabled."""
    db = await aiosqlite.connect(settings.DATABASE_PATH)
    await db.execute("PRAGMA journal_mode = WAL;")
    await db.execute("PRAGMA synchronous = NORMAL;")
    await db.execute("PRAGMA foreign_keys = ON;")
    db.row_factory = aiosqlite.Row
    return db
