"""
Database Migrations Module

Used to add new columns to existing tables or perform other migration tasks.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from core.database import DatabaseManager

logger = logging.getLogger(__name__)


# Migration definitions
# Each migration contains: table, column, sql
MIGRATIONS = [
    # Migration 1: Add source column to tags table
    {
        "table": "tags",
        "column": "source",
        "sql": "ALTER TABLE tags ADD COLUMN source TEXT DEFAULT 'user'",
    },
]


def column_exists(db: "DatabaseManager", table: str, column: str) -> bool:
    """Check if a column exists in a table"""
    try:
        cursor = db.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns
    except Exception:
        return False


def run_migrations(db: "DatabaseManager") -> None:
    """
    Execute database migrations
    
    Used to add new columns to existing tables. Uses ALTER TABLE ADD COLUMN,
    which in SQLite throws an error if the column already exists, so checks are needed first.
    
    Args:
        db: DatabaseManager instance
    """
    for migration in MIGRATIONS:
        if not column_exists(db, migration["table"], migration["column"]):
            try:
                db.execute(migration["sql"])
                logger.info("Migration applied: %s.%s", migration["table"], migration["column"])
            except Exception as e:
                # Ignore migration errors (column might already exist in some edge cases)
                if "duplicate column" not in str(e).lower():
                    logger.exception("Database migration failed: %s", migration)
