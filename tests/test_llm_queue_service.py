"""
LLM 队列管理服务测试
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.config_service import ConfigService
from services.llm_queue_service import LLMQueueService, QueueReorderPlan
from models.track import Track


class _FakeClient:
    def __init__(self, content: str):
        self._content = content

    def chat_completions(self, _messages):
        return self._content


class _DummyPlayer:
    def __init__(self, queue, current_index=0):
        self._queue = list(queue)
        self._current_index = current_index

    @property
    def queue(self):
        return self._queue.copy()

    @property
    def current_track(self):
        if 0 <= self._current_index < len(self._queue):
            return self._queue[self._current_index]
        return None

    def set_queue(self, tracks, start_index=0):
        self._queue = list(tracks)
        self._current_index = start_index
    
    def clear_queue(self):
        self._queue = []
        self._current_index = -1


class _FakeClientSeq:
    def __init__(self, contents):
        self._contents = list(contents)

    def chat_completions(self, _messages):
        if not self._contents:
            raise RuntimeError("no more responses")
        return self._contents.pop(0)


class _DummyLibrary:
    def __init__(self, tracks):
        self._tracks = list(tracks)
        self._id_map = {t.id: t for t in tracks}

    def query_tracks(self, **_kwargs):
        return []

    def iter_tracks_brief(self, batch_size=250, limit=None):
        rows = [
            {"id": t.id, "title": t.title, "artist_name": t.artist_name, "album_name": t.album_name}
            for t in self._tracks
        ]
        if limit is not None:
            rows = rows[: int(limit)]
        yield rows[: int(batch_size)]

    def get_tracks_by_ids(self, ids):
        return [self._id_map[i] for i in ids if i in self._id_map]


def test_parse_reorder_plan_strips_fences_and_filters_ids():
    ConfigService.reset_instance()
    try:
        t1 = Track(id="a", title="A")
        t2 = Track(id="b", title="B")
        queue = [t1, t2]

        content = """```json
{"ordered_track_ids":["b","b","nope","a"],"reason":"swap"}
```"""
        svc = LLMQueueService(config=ConfigService("config/does_not_exist.yaml"), client=_FakeClient(content))
        plan = svc.suggest_reorder("swap", queue, current_track_id="a")
        assert plan.ordered_track_ids == ["b", "a"]
        assert plan.reason == "swap"
    finally:
        ConfigService.reset_instance()


def test_suggest_reorder_empty_result_keeps_original():
    ConfigService.reset_instance()
    try:
        t1 = Track(id="a", title="A")
        t2 = Track(id="b", title="B")
        queue = [t1, t2]

        svc = LLMQueueService(
            config=ConfigService("config/does_not_exist.yaml"),
            client=_FakeClient('{"ordered_track_ids": []}'),
        )
        plan = svc.suggest_reorder("whatever", queue, current_track_id="a")
        assert plan.ordered_track_ids == ["a", "b"]
    finally:
        ConfigService.reset_instance()


def test_apply_reorder_plan_preserves_current_track_index():
    t1 = Track(id="a", title="A")
    t2 = Track(id="b", title="B")
    t3 = Track(id="c", title="C")

    player = _DummyPlayer([t1, t2, t3], current_index=1)  # current=b
    svc = LLMQueueService(config=ConfigService("config/does_not_exist.yaml"), client=_FakeClient("{}"))

    plan = QueueReorderPlan(ordered_track_ids=["c", "b"])
    new_queue, new_index = svc.apply_reorder_plan(player, plan)

    assert [t.id for t in new_queue] == ["c", "b", "a"]
    assert new_index == 1
    assert player.current_track.id == "b"


def test_suggest_reorder_can_clear_queue_when_flag_true():
    ConfigService.reset_instance()
    try:
        t1 = Track(id="a", title="A")
        t2 = Track(id="b", title="B")
        queue = [t1, t2]

        svc = LLMQueueService(
            config=ConfigService("config/does_not_exist.yaml"),
            client=_FakeClient('{"clear_queue": true, "ordered_track_ids": []}'),
        )
        plan = svc.suggest_reorder("clear", queue, current_track_id="a")
        assert plan.clear_queue is True
        assert plan.ordered_track_ids == []
    finally:
        ConfigService.reset_instance()


def test_apply_reorder_plan_clear_queue():
    t1 = Track(id="a", title="A")
    t2 = Track(id="b", title="B")
    player = _DummyPlayer([t1, t2], current_index=0)
    svc = LLMQueueService(config=ConfigService("config/does_not_exist.yaml"), client=_FakeClient("{}"))

    plan = QueueReorderPlan(ordered_track_ids=[], clear_queue=True)
    new_queue, new_index = svc.apply_reorder_plan(player, plan)

    assert new_queue == []
    assert new_index == -1
    assert player.queue == []
    assert player.current_track is None


def test_parse_plan_includes_library_request():
    ConfigService.reset_instance()
    try:
        t1 = Track(id="a", title="A")
        queue = [t1]

        content = """{
  "library_request": {"mode": "replace", "genre": "摇滚", "limit": 10, "shuffle": true},
  "ordered_track_ids": [],
  "reason": "调取摇滚"
}"""
        svc = LLMQueueService(config=ConfigService("config/does_not_exist.yaml"), client=_FakeClient(content))
        plan = svc.suggest_reorder("调取摇滚音乐进队列", queue, current_track_id="a")
        assert plan.library_request is not None
        assert plan.library_request.genre == "摇滚"
        assert plan.library_request.mode == "replace"
        assert plan.ordered_track_ids == []
    finally:
        ConfigService.reset_instance()


def test_apply_plan_semantic_fallback_selects_tracks_when_no_genre_tags():
    ConfigService.reset_instance()
    try:
        t1 = Track(id="t1", title="Back In Black", artist_name="AC/DC", album_name="Back In Black")
        t2 = Track(id="t2", title="Numb", artist_name="Linkin Park", album_name="Meteora")
        library = _DummyLibrary([t1, t2])

        # apply_plan 会在 query_tracks 为空时触发语义筛选：
        # 1) 每批返回 selected_track_ids
        client = _FakeClientSeq(['{"selected_track_ids":["t2","t1"],"reason":"rock-ish"}'])
        svc = LLMQueueService(config=ConfigService("config/does_not_exist.yaml"), client=client)

        player = _DummyPlayer([Track(id="x", title="X")], current_index=0)
        plan = QueueReorderPlan(
            ordered_track_ids=[],
            library_request=svc._parse_reorder_plan(
                '{"library_request":{"mode":"replace","genre":"摇滚","limit":2,"semantic_fallback":true},"ordered_track_ids":[]}',
                known_ids=set(),
            ).library_request,
            instruction="从音乐库调取摇滚音乐进队列",
        )

        new_queue, new_index = svc.apply_plan(player, plan, library=library)
        assert [t.id for t in new_queue] == ["t2", "t1"]
        assert new_index == 0
    finally:
        ConfigService.reset_instance()
