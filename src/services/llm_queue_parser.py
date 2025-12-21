"""
LLM Queue Parser Module

Responsible for constructing LLM messages and parsing LLM responses.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from models.track import Track
from models.queue_plan import LLMQueueError, LibraryQueueRequest, QueueReorderPlan
from services.llm_response_parser import strip_code_fences
from services.llm_response_utils import (
    build_semantic_select_messages,
    build_semantic_finalize_messages,
    parse_selected_track_ids,
)

logger = logging.getLogger(__name__)


class LLMQueueParser:
    """
    LLM Queue Parser
    
    Handles LLM message construction and response parsing.
    """
    
    def __init__(self):
        pass
    
    def build_reorder_messages(
        self,
        instruction: str,
        queue: Sequence[Track],
        current_track_id: Optional[str],
        library_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """Build queue reorder message"""
        def to_item(t: Track) -> Dict[str, Any]:
            return {
                "id": t.id,
                "title": t.title,
                "artist": t.artist_name,
                "album": t.album_name,
                "duration_ms": t.duration_ms,
            }

        schema = {
            "clear_queue": False,
            "library_request": {
                "mode": "replace|append",
                "query": "optional, keyword (matches title/artist/album/genre)",
                "genre": "optional, e.g., Rock",
                "artist": "optional",
                "album": "optional",
                "limit": 30,
                "shuffle": True,
                "semantic_fallback": True,
            },
            "ordered_track_ids": ["<track_id>", "<track_id>"],
            "reason": "short explanation (optional)",
        }

        user_payload = {
            "instruction": instruction,
            "current_track_id": current_track_id,
            "queue": [to_item(t) for t in queue],
            "library_context": library_context or {},
            "response_schema": schema,
            "rules": [
                "Only output pure JSON (no markdown, no code blocks).",
                "If the instruction is to clear the queue, set clear_queue=true and ordered_track_ids to an empty list.",
                "If the instruction is to fetch/add/play music from the library, set library_request (and set ordered_track_ids to empty).",
                "When library_context.has_genre_tags=false, the library might lack genre tags: if filtering by genre/query fails, ensure library_request.semantic_fallback=true (let the client perform semantic selection).",
                "ordered_track_ids can only contain IDs present in the current queue.",
                "Reducing ordered_track_ids implies removing tracks; unmentioned tracks will be appended to the end by the client.",
                "If unsure, return the original order.",
            ],
        }

        system = (
            "You are the playback queue manager for a local music player."
            "Strictly output JSON according to the given schema."
            "Do not output anything other than JSON."
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
    
    def parse_reorder_plan(self, content: str, known_ids: set[str]) -> QueueReorderPlan:
        """Parse the reorder plan"""
        raw = strip_code_fences(content).strip()

        try:
            data = json.loads(raw)
        except Exception as e:
            raise LLMQueueError(f"LLM returned non-JSON: {raw[:200]}") from e

        clear_queue = bool(data.get("clear_queue", False))

        library_request = None
        lr = data.get("library_request", None)
        if isinstance(lr, dict):
            mode = str(lr.get("mode", "replace") or "replace").strip().lower()
            if mode not in {"replace", "append"}:
                mode = "replace"

            def _s(key: str) -> str:
                v = lr.get(key, "")
                return v.strip() if isinstance(v, str) else ""

            limit = lr.get("limit", 30)
            try:
                limit = int(limit)
            except Exception:
                limit = 30
            limit = max(1, min(200, limit))

            shuffle = bool(lr.get("shuffle", True))
            semantic_fallback = bool(lr.get("semantic_fallback", True))

            q = _s("query")
            genre = _s("genre")
            artist = _s("artist")
            album = _s("album")
            if any([q, genre, artist, album]):
                library_request = LibraryQueueRequest(
                    mode=mode,
                    query=q,
                    genre=genre,
                    artist=artist,
                    album=album,
                    limit=limit,
                    shuffle=shuffle,
                    semantic_fallback=semantic_fallback,
                )

        ordered = data.get("ordered_track_ids", [])
        if not isinstance(ordered, list):
            ordered = []

        normalized: List[str] = []
        seen = set()
        for v in ordered:
            if not isinstance(v, str):
                continue
            if v in known_ids and v not in seen:
                normalized.append(v)
                seen.add(v)

        reason = data.get("reason", "")
        if not isinstance(reason, str):
            reason = ""

        return QueueReorderPlan(
            ordered_track_ids=normalized,
            reason=reason,
            clear_queue=clear_queue,
            library_request=library_request,
        )
    
    # ===== Delegated methods to shared module =====
    
    def build_semantic_select_messages(
        self,
        instruction: str,
        request: LibraryQueueRequest,
        candidates: List[Dict[str, Any]],
        max_select: int,
        total_sent: int,
        total_limit: int,
    ) -> List[Dict[str, str]]:
        """Build semantic selection message (delegated)"""
        return build_semantic_select_messages(
            instruction, request, candidates, max_select, total_sent, total_limit
        )
    
    def build_semantic_finalize_messages(
        self,
        instruction: str,
        request: LibraryQueueRequest,
        candidates: List[Dict[str, str]],
        limit: int,
    ) -> List[Dict[str, str]]:
        """Build semantic final selection message (delegated)"""
        return build_semantic_finalize_messages(instruction, request, candidates, limit)
    
    def parse_selected_track_ids(self, content: str, known_ids: set[str]) -> List[str]:
        """Parse selected track IDs (delegated)"""
        return parse_selected_track_ids(content, known_ids)