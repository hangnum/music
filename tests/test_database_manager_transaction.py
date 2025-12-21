"""
DatabaseManager transaction behavior tests.

These tests are used to detect early issues such as transactions failing to 
rollback/commit, or broken exception chains.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _reset_db_manager():
    from core.database import DatabaseManager

    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


def _insert_playlist_row(db, playlist_id: str):
    db.execute(
        "INSERT INTO playlists (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (playlist_id, "P", datetime.now().isoformat(), datetime.now().isoformat()),
    )


def test_transaction_commits_on_success(tmp_path: Path):
    from core.database import DatabaseManager

    db = DatabaseManager(str(tmp_path / "t.db"))

    with db.transaction():
        _insert_playlist_row(db, "p1")

    row = db.fetch_one("SELECT id FROM playlists WHERE id = ?", ("p1",))
    assert row is not None


def test_transaction_rolls_back_on_exception(tmp_path: Path):
    from core.database import DatabaseManager

    db = DatabaseManager(str(tmp_path / "t.db"))

    with pytest.raises(RuntimeError):
        with db.transaction():
            _insert_playlist_row(db, "p1")
            raise RuntimeError("boom")

    row = db.fetch_one("SELECT id FROM playlists WHERE id = ?", ("p1",))
    assert row is None

