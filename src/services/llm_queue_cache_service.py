"""
LLM 队列缓存 / 查询历史服务

目标：
- 将 LLM 生成的播放队列持久化到本地 DB，支持重启后复用
- 对相同/相近的指令命中缓存，避免重复消耗 token
- 提供“查询历史 -> 一键加载上次队列”的基础能力
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json
import re

from core.database import DatabaseManager
from models.track import Track
from services.config_service import ConfigService
from services.library_service import LibraryService


@dataclass(frozen=True)
class LLMQueueHistoryEntry:
    id: int
    instruction: str
    normalized_instruction: str
    label: str
    track_ids: List[str]
    start_index: int
    created_at: str


class LLMQueueCacheService:
    def __init__(self, db: Optional[DatabaseManager] = None, config: Optional[ConfigService] = None):
        self._db = db or DatabaseManager()
        self._config = config or ConfigService()

    def enabled(self) -> bool:
        return bool(self._config.get("llm.queue_manager.cache.enabled", True))

    def normalize_instruction(self, instruction: str) -> str:
        text = (instruction or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def get_cached_entry(self, instruction: str) -> Optional[LLMQueueHistoryEntry]:
        if not self.enabled():
            return None

        normalized = self.normalize_instruction(instruction)
        if not normalized:
            return None

        ttl_days = int(self._config.get("llm.queue_manager.cache.ttl_days", 30))
        params: Tuple[Any, ...] = (normalized,)
        ttl_clause = ""
        if ttl_days > 0:
            ttl_clause = " AND created_at >= datetime('now', ?)"
            params = (normalized, f"-{ttl_days} day")

        row = self._db.fetch_one(
            "SELECT id, instruction, normalized_instruction, label, track_ids_json, start_index, created_at "
            "FROM llm_queue_history "
            f"WHERE normalized_instruction = ?{ttl_clause} "
            "ORDER BY id DESC LIMIT 1",
            params,
        )
        if not row:
            return None

        track_ids = self._parse_track_ids(row.get("track_ids_json", ""))
        if not track_ids:
            return None

        return LLMQueueHistoryEntry(
            id=int(row["id"]),
            instruction=str(row.get("instruction", "")),
            normalized_instruction=str(row.get("normalized_instruction", "")),
            label=str(row.get("label", "")),
            track_ids=track_ids,
            start_index=int(row.get("start_index", 0) or 0),
            created_at=str(row.get("created_at", "")),
        )

    def save_history(
        self,
        instruction: str,
        track_ids: List[str],
        start_index: int = 0,
        label: Optional[str] = None,
        plan_json: Optional[str] = None,
    ) -> int:
        if not self.enabled():
            return 0

        normalized = self.normalize_instruction(instruction)
        label_text = (label or instruction or "").strip() or normalized or "未命名"

        ids = [t for t in track_ids if isinstance(t, str) and t]
        if not ids:
            return 0

        max_items = int(self._config.get("llm.queue_manager.cache.max_items", 200))
        if max_items > 0:
            ids = ids[:max_items]

        raw_ids = json.dumps(ids, ensure_ascii=False)

        self._db.execute(
            "INSERT INTO llm_queue_history(instruction, normalized_instruction, label, track_ids_json, start_index, plan_json) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (instruction or "", normalized, label_text, raw_ids, int(start_index or 0), plan_json),
        )
        self._db.commit()

        row = self._db.fetch_one("SELECT last_insert_rowid() AS id")
        entry_id = int(row["id"]) if row and row.get("id") is not None else 0

        self._prune_history()
        return entry_id

    def list_history(self, limit: int = 30) -> List[LLMQueueHistoryEntry]:
        limit = max(1, int(limit or 30))

        rows = self._db.fetch_all(
            "SELECT id, instruction, normalized_instruction, label, track_ids_json, start_index, created_at "
            "FROM llm_queue_history "
            "ORDER BY id DESC "
            "LIMIT ?",
            (limit,),
        )

        out: List[LLMQueueHistoryEntry] = []
        for row in rows:
            track_ids = self._parse_track_ids(row.get("track_ids_json", ""))
            out.append(
                LLMQueueHistoryEntry(
                    id=int(row["id"]),
                    instruction=str(row.get("instruction", "")),
                    normalized_instruction=str(row.get("normalized_instruction", "")),
                    label=str(row.get("label", "")),
                    track_ids=track_ids,
                    start_index=int(row.get("start_index", 0) or 0),
                    created_at=str(row.get("created_at", "")),
                )
            )
        return out

    def load_entry_queue(self, entry_id: int, library: LibraryService) -> Optional[Tuple[List[Track], int]]:
        row = self._db.fetch_one(
            "SELECT track_ids_json, start_index FROM llm_queue_history WHERE id = ?",
            (int(entry_id),),
        )
        if not row:
            return None

        track_ids = self._parse_track_ids(row.get("track_ids_json", ""))
        if not track_ids:
            return None

        tracks = library.get_tracks_by_ids(track_ids)
        by_id = {t.id: t for t in tracks if isinstance(t, Track) and t.id}
        ordered = [by_id[t_id] for t_id in track_ids if t_id in by_id]
        if not ordered:
            return None

        start_index = int(row.get("start_index", 0) or 0)
        start_index = max(0, min(start_index, max(0, len(ordered) - 1)))
        return (ordered, start_index)

    def load_cached_queue(self, instruction: str, library: LibraryService) -> Optional[Tuple[List[Track], int, LLMQueueHistoryEntry]]:
        entry = self.get_cached_entry(instruction)
        if not entry:
            return None

        result = self.load_entry_queue(entry.id, library)
        if not result:
            return None
        queue, start_index = result
        return (queue, start_index, entry)

    def _parse_track_ids(self, raw: str) -> List[str]:
        try:
            data = json.loads(raw or "[]")
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [t for t in data if isinstance(t, str) and t]

    def _prune_history(self) -> None:
        max_history = int(self._config.get("llm.queue_manager.cache.max_history", 80))
        if max_history <= 0:
            return

        rows = self._db.fetch_all(
            "SELECT id FROM llm_queue_history ORDER BY id DESC LIMIT -1 OFFSET ?",
            (max_history,),
        )
        ids = [int(r["id"]) for r in rows if r.get("id") is not None]
        if not ids:
            return

        placeholders = ",".join(["?"] * len(ids))
        self._db.execute(f"DELETE FROM llm_queue_history WHERE id IN ({placeholders})", tuple(ids))
        self._db.commit()
