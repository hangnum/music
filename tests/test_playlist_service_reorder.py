"""
PlaylistService 的补充测试：覆盖 add/remove/reorder 的关键路径。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from models.track import Track


@pytest.fixture(autouse=True)
def _reset_singletons():
    from core.database import DatabaseManager

    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


def _setup_db(tmp_path: Path):
    from core.database import DatabaseManager

    return DatabaseManager(str(tmp_path / "playlist.db"))


def _insert_track_row(db, track_id: str, title: str):
    db.insert(
        "tracks",
        {
            "id": track_id,
            "title": title,
            "file_path": f"{track_id}.mp3",
        },
    )


def test_reorder_track_updates_positions(tmp_path: Path):
    from services.playlist_service import PlaylistService

    db = _setup_db(tmp_path)
    _insert_track_row(db, "t1", "A")
    _insert_track_row(db, "t2", "B")
    _insert_track_row(db, "t3", "C")

    svc = PlaylistService(db)
    playlist = svc.create("P")

    assert svc.add_track(playlist.id, Track(id="t1", title="A")) is True
    assert svc.add_track(playlist.id, Track(id="t2", title="B")) is True
    assert svc.add_track(playlist.id, Track(id="t3", title="C")) is True

    assert [t.id for t in svc.get_tracks(playlist.id)] == ["t1", "t2", "t3"]

    # 将 t1 从 1 移动到 3
    assert svc.reorder_track(playlist.id, "t1", new_position=3) is True
    assert [t.id for t in svc.get_tracks(playlist.id)] == ["t2", "t3", "t1"]

    # 将 t3 从 2 移动到 1
    assert svc.reorder_track(playlist.id, "t3", new_position=1) is True
    assert [t.id for t in svc.get_tracks(playlist.id)] == ["t3", "t2", "t1"]


def test_remove_track_from_playlist(tmp_path: Path):
    from services.playlist_service import PlaylistService

    db = _setup_db(tmp_path)
    _insert_track_row(db, "t1", "A")
    _insert_track_row(db, "t2", "B")

    svc = PlaylistService(db)
    playlist = svc.create("P")

    assert svc.add_track(playlist.id, Track(id="t1", title="A")) is True
    assert svc.add_track(playlist.id, Track(id="t2", title="B")) is True

    assert svc.remove_track(playlist.id, "t1") is True
    assert [t.id for t in svc.get_tracks(playlist.id)] == ["t2"]

    # 不存在的 track_id 应返回 False
    assert svc.remove_track(playlist.id, "missing") is False

