"""
Tests for playback queue persistence and LLM queue cache/history.
"""

import os
import pytest



@pytest.fixture(autouse=True)
def _reset_singletons():
    from core.database import DatabaseManager
    from services.config_service import ConfigService

    DatabaseManager.reset_instance()
    ConfigService.reset_instance()
    yield
    DatabaseManager.reset_instance()
    ConfigService.reset_instance()


class DummyPlayer:
    def __init__(self):
        self._queue = []
        self._current_index = -1

    @property
    def queue(self):
        return list(self._queue)

    @property
    def current_track(self):
        if 0 <= self._current_index < len(self._queue):
            return self._queue[self._current_index]
        return None

    def set_queue(self, tracks, start_index=0):
        self._queue = list(tracks)
        self._current_index = int(start_index) if self._queue else -1


def _setup_db(tmp_path):
    from core.database import DatabaseManager

    DatabaseManager.reset_instance()
    db_path = tmp_path / "test_music.db"
    db = DatabaseManager(str(db_path))
    return db


def _setup_config(tmp_path):
    from services.config_service import ConfigService

    ConfigService.reset_instance()
    config = ConfigService(str(tmp_path / "config.yaml"))
    config.reset()
    return config


def _insert_track(db, track_id, title):
    db.insert(
        "tracks",
        {
            "id": track_id,
            "title": title,
            "file_path": f"D:/Music/{track_id}.mp3",
        },
    )


def test_queue_persistence_round_trip(tmp_path):
    from services.queue_persistence_service import QueuePersistenceService
    from services.library_service import LibraryService

    db = _setup_db(tmp_path)
    config = _setup_config(tmp_path)

    config.set("playback.persist_queue", True)
    config.set("playback.persist_queue_max_items", 500)

    track_ids = ["t1", "t2", "t3"]
    for tid in track_ids:
        _insert_track(db, tid, f"title-{tid}")

    library = LibraryService(db)

    persistence = QueuePersistenceService(db=db, config=config)
    persistence.save_last_queue(track_ids, current_track_id="t2")

    player = DummyPlayer()
    assert persistence.restore_last_queue(player, library) is True
    assert [t.id for t in player.queue] == track_ids
    assert player.current_track.id == "t2"


def test_llm_queue_cache_save_and_load(tmp_path):
    from services.llm_queue_cache_service import LLMQueueCacheService
    from services.library_service import LibraryService

    db = _setup_db(tmp_path)
    config = _setup_config(tmp_path)

    config.set("llm.queue_manager.cache.enabled", True)
    config.set("llm.queue_manager.cache.max_history", 80)
    config.set("llm.queue_manager.cache.max_items", 200)
    config.set("llm.queue_manager.cache.ttl_days", 30)

    track_ids = ["a1", "a2"]
    for tid in track_ids:
        _insert_track(db, tid, f"title-{tid}")

    library = LibraryService(db)
    cache = LLMQueueCacheService(db=db, config=config)

    entry_id = cache.save_history("Relaxing", track_ids, start_index=1, label="Relaxing")
    assert entry_id > 0

    loaded = cache.load_cached_queue("Relaxing", library)
    assert loaded is not None
    queue, start_index, entry = loaded
    assert [t.id for t in queue] == track_ids
    assert start_index == 1
    assert entry.id == entry_id

    history = cache.list_history(limit=10)
    assert history
    assert history[0].label == "Relaxing"


def test_llm_queue_cache_prunes_to_max_history(tmp_path):
    from services.llm_queue_cache_service import LLMQueueCacheService

    db = _setup_db(tmp_path)
    config = _setup_config(tmp_path)

    config.set("llm.queue_manager.cache.enabled", True)
    config.set("llm.queue_manager.cache.max_history", 1)

    cache = LLMQueueCacheService(db=db, config=config)

    cache.save_history("q1", ["x1"], start_index=0, label="q1")
    cache.save_history("q2", ["x2"], start_index=0, label="q2")

    history = cache.list_history(limit=10)
    assert len(history) == 1
    assert history[0].label == "q2"
