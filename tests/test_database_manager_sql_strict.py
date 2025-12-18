"""
Stricter DatabaseManager SQL/transaction/concurrency tests.

These tests aim to catch subtle write/commit issues early:
- Writes wrapped by leading comments should still be detected and committed.
- CTE-based writes (`WITH ... INSERT/UPDATE/...`) should still commit outside explicit transactions.
- High-level helpers (insert/update/delete/execute_many) must respect `transaction()` rollback.
"""

from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _reset_db_manager():
    from core.database import DatabaseManager

    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


def _raw_count_rows(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
        assert row is not None
        return int(row[0])
    finally:
        conn.close()


def test_execute_autocommits_write_with_leading_comment(tmp_path: Path):
    from core.database import DatabaseManager

    db_path = tmp_path / "comment_autocommit.db"
    db = DatabaseManager(str(db_path))
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, v INTEGER NOT NULL)")

    db.execute("-- leading comment\nINSERT INTO t (v) VALUES (?)", (1,))

    assert _raw_count_rows(db_path) == 1


def test_execute_autocommits_cte_insert(tmp_path: Path):
    from core.database import DatabaseManager

    db_path = tmp_path / "cte_autocommit.db"
    db = DatabaseManager(str(db_path))
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, v INTEGER NOT NULL)")

    db.execute(
        "WITH x(v) AS (SELECT ?) INSERT INTO t (v) SELECT v FROM x",
        (1,),
    )

    assert _raw_count_rows(db_path) == 1


def test_helpers_respect_transaction_rollback(tmp_path: Path):
    from core.database import DatabaseManager

    db_path = tmp_path / "helpers_tx.db"
    db = DatabaseManager(str(db_path))
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, v INTEGER NOT NULL)")

    with pytest.raises(RuntimeError):
        with db.transaction():
            db.insert("t", {"v": 1})
            db.update("t", {"v": 2}, "id = ?", (1,))
            db.delete("t", "id = ?", (1,))
            db.execute_many("INSERT INTO t (v) VALUES (?)", [(10,), (11,)])
            raise RuntimeError("boom")

    assert _raw_count_rows(db_path) == 0


def test_concurrent_writes_with_comment_prefix_do_not_lock(tmp_path: Path):
    from core.database import DatabaseManager

    db_path = tmp_path / "concurrent_comment.db"
    db = DatabaseManager(str(db_path))
    db.execute(
        "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, thread_id INTEGER, i INTEGER)"
    )

    num_threads = 8
    writes_per_thread = 40
    start = threading.Barrier(num_threads)

    def writer(thread_id: int) -> None:
        local_db = DatabaseManager(str(db_path))
        try:
            local_db._conn.execute("PRAGMA busy_timeout = 1")
            start.wait(timeout=5)
            for i in range(writes_per_thread):
                local_db.execute(
                    "-- comment\nINSERT INTO t (thread_id, i) VALUES (?, ?)",
                    (thread_id, i),
                )
        finally:
            local_db.close()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(writer, t) for t in range(num_threads)]
        for f in futures:
            f.result()

    row = db.fetch_one("SELECT COUNT(*) AS cnt FROM t")
    assert row is not None
    assert row["cnt"] == num_threads * writes_per_thread

