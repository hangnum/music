"""
播放队列持久化服务

支持：
- 退出/重启后自动恢复上一次播放队列
- 在队列变化/开始播放时持续保存当前队列状态
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import json

from core.database import DatabaseManager
from core.event_bus import EventBus, EventType
from services.config_service import ConfigService
from services.library_service import LibraryService
from models.track import Track


class QueuePersistenceService:
    LAST_QUEUE_KEY = "playback.last_queue"

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        config: Optional[ConfigService] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self._db = db or DatabaseManager()
        self._config = config or ConfigService()
        self._event_bus = event_bus or EventBus()

        self._enabled = bool(self._config.get("playback.persist_queue", True))
        self._max_items = int(self._config.get("playback.persist_queue_max_items", 500))

        self._player: Optional[Any] = None
        self._sub_ids: List[str] = []
        self._suppress = False

    def attach(self, player: Any) -> None:
        """绑定 player 并开始监听事件以自动持久化。"""
        self._player = player
        if not self._enabled:
            return

        self._sub_ids.append(self._event_bus.subscribe(EventType.QUEUE_CHANGED, self._on_queue_changed))
        self._sub_ids.append(self._event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started))

    def shutdown(self) -> None:
        """取消订阅（用于窗口关闭时清理）。"""
        for sub_id in self._sub_ids:
            try:
                self._event_bus.unsubscribe(sub_id)
            except Exception:
                pass
        self._sub_ids.clear()
        self._player = None

    def save_last_queue(self, track_ids: List[str], current_track_id: Optional[str]) -> None:
        """保存播放队列（track id 列表 + 当前曲目 id）。"""
        if not self._enabled:
            return

        ids = [t for t in track_ids if isinstance(t, str) and t]
        if self._max_items > 0:
            ids = ids[: self._max_items]

        payload: Dict[str, Any] = {
            "track_ids": ids,
            "current_track_id": current_track_id or "",
        }

        raw = json.dumps(payload, ensure_ascii=False)
        self._db.execute(
            "INSERT OR REPLACE INTO app_state(key, value, updated_at) VALUES(?, ?, CURRENT_TIMESTAMP)",
            (self.LAST_QUEUE_KEY, raw),
        )
        self._db._conn.commit()

    def load_last_queue(self) -> Tuple[List[str], Optional[str]]:
        """读取播放队列（track id 列表 + 当前曲目 id）。"""
        row = self._db.fetch_one("SELECT value FROM app_state WHERE key = ?", (self.LAST_QUEUE_KEY,))
        if not row or not row.get("value"):
            return ([], None)

        try:
            data = json.loads(row["value"])
        except Exception:
            return ([], None)

        track_ids = data.get("track_ids") if isinstance(data, dict) else None
        current_track_id = data.get("current_track_id") if isinstance(data, dict) else None

        ids = [t for t in (track_ids or []) if isinstance(t, str) and t]
        cur = current_track_id if isinstance(current_track_id, str) and current_track_id else None
        return (ids, cur)

    def restore_last_queue(self, player: Any, library: LibraryService) -> bool:
        """从持久化状态恢复队列并设置到 player。"""
        if not self._enabled:
            return False

        track_ids, current_track_id = self.load_last_queue()
        if not track_ids:
            return False

        tracks = library.get_tracks_by_ids(track_ids)
        by_id = {t.id: t for t in tracks if isinstance(t, Track) and t.id}
        ordered: List[Track] = [by_id[t_id] for t_id in track_ids if t_id in by_id]
        if not ordered:
            return False

        start_index = 0
        if current_track_id and current_track_id in by_id:
            try:
                start_index = [t.id for t in ordered].index(current_track_id)
            except ValueError:
                start_index = 0

        self._suppress = True
        try:
            player.set_queue(ordered, start_index)
        finally:
            self._suppress = False

        return True

    def persist_from_player(self) -> None:
        """从已绑定的 player 读取状态并持久化。"""
        if not self._enabled or self._player is None:
            return

        queue = list(getattr(self._player, "queue", []) or [])
        current = getattr(self._player, "current_track", None)
        current_id = getattr(current, "id", None) if current else None
        self.save_last_queue([getattr(t, "id", "") for t in queue], current_id)

    def _on_queue_changed(self, _queue: Any) -> None:
        if self._suppress:
            return
        self.persist_from_player()

    def _on_track_started(self, _track: Any) -> None:
        if self._suppress:
            return
        self.persist_from_player()

