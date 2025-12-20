"""
数据库迁移模块

用于向已存在的表添加新列或执行其他迁移操作。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from core.database import DatabaseManager

logger = logging.getLogger(__name__)


# 迁移定义列表
# 每个迁移包含: table, column, sql
MIGRATIONS = [
    # Migration 1: 为 tags 表添加 source 列
    {
        "table": "tags",
        "column": "source",
        "sql": "ALTER TABLE tags ADD COLUMN source TEXT DEFAULT 'user'",
    },
]


def column_exists(db: "DatabaseManager", table: str, column: str) -> bool:
    """检查表中是否存在某列"""
    try:
        cursor = db.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns
    except Exception:
        return False


def run_migrations(db: "DatabaseManager") -> None:
    """
    执行数据库迁移
    
    用于向已存在的表添加新列。使用 ALTER TABLE ADD COLUMN，
    该语句在 SQLite 中如果列已存在会报错，所以需要先检查。
    
    Args:
        db: DatabaseManager 实例
    """
    for migration in MIGRATIONS:
        if not column_exists(db, migration["table"], migration["column"]):
            try:
                db.execute(migration["sql"])
                logger.info("Migration applied: %s.%s", migration["table"], migration["column"])
            except Exception as e:
                # 忽略迁移错误（列可能已存在于某些边缘情况）
                if "duplicate column" not in str(e).lower():
                    logger.exception("数据库迁移失败: %s", migration)
