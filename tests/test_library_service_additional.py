"""
LibraryService 的额外单元测试（覆盖查询/分页/统计分支）。
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _reset_singletons():
    from core.database import DatabaseManager

    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


def _setup_db(tmp_path: Path):
    from core.database import DatabaseManager

    return DatabaseManager(str(tmp_path / "lib.db"))


def _insert_track(db, *, track_id: str, title: str, file_path: str, artist: str = "", album: str = "", genre=None):
    db.insert(
        "tracks",
        {
            "id": track_id,
            "title": title,
            "file_path": file_path,
            "artist_name": artist,
            "album_name": album,
            "genre": genre,
            "track_number": 1,
        },
    )


def test_iter_tracks_brief_paginates_and_honors_limit(tmp_path: Path):
    from services.library_service import LibraryService

    db = _setup_db(tmp_path)

    # iter_tracks_brief 会将 batch_size 夹到 [50, 800]，用 51 条数据覆盖分页逻辑
    for i in range(51):
        tid = f"t{i:02d}"
        _insert_track(db, track_id=tid, title=f"Song {i:02d}", file_path=f"{tid}.mp3", artist="A", album="X")

    library = LibraryService(db)

    batches = list(library.iter_tracks_brief(batch_size=2))
    assert [len(b) for b in batches] == [50, 1]

    limited = list(library.iter_tracks_brief(batch_size=2, limit=2))
    assert [len(b) for b in limited] == [2]


def test_get_tracks_by_ids_filters_invalid_and_returns_tracks(tmp_path: Path):
    from services.library_service import LibraryService

    db = _setup_db(tmp_path)
    _insert_track(db, track_id="t1", title="A", file_path="a.mp3")
    _insert_track(db, track_id="t2", title="B", file_path="b.mp3")

    library = LibraryService(db)

    tracks = library.get_tracks_by_ids(["t1", "", None, "t2", "missing"])
    assert {t.id for t in tracks} == {"t1", "t2"}

    assert library.get_tracks_by_ids([]) == []


def test_get_top_genres_ignores_empty_and_orders_by_count(tmp_path: Path):
    from services.library_service import LibraryService

    db = _setup_db(tmp_path)
    _insert_track(db, track_id="t1", title="A", file_path="a.mp3", genre="Rock")
    _insert_track(db, track_id="t2", title="B", file_path="b.mp3", genre="Rock")
    _insert_track(db, track_id="t3", title="C", file_path="c.mp3", genre="Pop")
    _insert_track(db, track_id="t4", title="D", file_path="d.mp3", genre="")
    _insert_track(db, track_id="t5", title="E", file_path="e.mp3", genre=None)

    library = LibraryService(db)

    genres = library.get_top_genres(limit="not-an-int")
    assert genres[:2] == ["Rock", "Pop"]


def test_update_play_stats_affects_recent_and_most_played(tmp_path: Path):
    from services.library_service import LibraryService

    db = _setup_db(tmp_path)
    _insert_track(db, track_id="t1", title="A", file_path="a.mp3")
    _insert_track(db, track_id="t2", title="B", file_path="b.mp3")

    library = LibraryService(db)
    library.update_play_stats("t2")
    library.update_play_stats("t2")
    library.update_play_stats("t1")

    most = library.get_most_played_tracks(limit=10)
    assert [t.id for t in most][:2] == ["t2", "t1"]

    recent = library.get_recent_tracks(limit=10)
    assert recent
    assert {t.id for t in recent} == {"t1", "t2"}
