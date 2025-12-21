"""
LLM Semantic Selector Module

Responsible for semantic filtering and track selection from the music library.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from models.track import Track
from models.queue_plan import LibraryQueueRequest, QueueReorderPlan
from services.llm_response_utils import (
    build_semantic_select_messages,
    build_semantic_finalize_messages,
    parse_selected_track_ids,
    parse_reorder_plan_from_response,
)

logger = logging.getLogger(__name__)


class LLMSemanticSelector:
    """
    LLM Semantic Selector
    
    Performs semantic filtering and refinement from the music library.
    """
    
    def __init__(self, client: Any, config: Any):
        """
        Initialize the semantic selector.
        
        Args:
            client: LLM provider
            config: Configuration service
        """
        self._client = client
        self._config = config
    
    def semantic_select_tracks_from_library(
        self,
        instruction: str,
        library: Any,
        request: LibraryQueueRequest,
        limit: int,
    ) -> List[Track]:
        """Semantically select tracks from the music library."""
        if not instruction.strip():
            return []

        max_catalog_items = int(self._config.get("llm.queue_manager.semantic_fallback.max_catalog_items", 1500))
        batch_size = int(self._config.get("llm.queue_manager.semantic_fallback.batch_size", 250))
        per_batch_pick = int(self._config.get("llm.queue_manager.semantic_fallback.per_batch_pick", 8))
        max_catalog_items = max(50, min(20000, max_catalog_items))
        batch_size = max(50, min(800, batch_size))
        per_batch_pick = max(1, min(30, per_batch_pick))

        from models.queue_plan import LLMQueueError
        if not hasattr(library, "iter_tracks_brief") or not hasattr(library, "get_tracks_by_ids"):
            raise LLMQueueError("LibraryService missing 'iter_tracks_brief' or 'get_tracks_by_ids'; semantic filtering unavailable.")

        candidate_briefs: List[Dict[str, str]] = []
        selected_ids: List[str] = []
        seen = set()
        total_sent = 0

        for batch in library.iter_tracks_brief(batch_size=batch_size, limit=max_catalog_items):
            if not batch:
                break
            total_sent += len(batch)

            known = {str(r.get("id", "")) for r in batch if r.get("id")}
            messages = build_semantic_select_messages(
                instruction=instruction,
                request=request,
                candidates=batch,
                max_select=per_batch_pick,
                total_sent=total_sent,
                total_limit=max_catalog_items,
            )
            content = self._client.chat_completions(messages)
            ids = parse_selected_track_ids(content, known)
            for track_id in ids:
                if track_id not in seen:
                    seen.add(track_id)
                    selected_ids.append(track_id)

            # Record briefs for final selection
            for r in batch:
                rid = str(r.get("id", ""))
                if rid and rid in seen:
                    candidate_briefs.append(
                        {
                            "id": rid,
                            "title": str(r.get("title", "") or ""),
                            "artist_name": str(r.get("artist_name", "") or ""),
                            "album_name": str(r.get("album_name", "") or ""),
                        }
                    )

        if not selected_ids:
            return []

        final_ids = selected_ids[:limit]
        if len(selected_ids) > limit:
            known_ids = {c["id"] for c in candidate_briefs}
            messages = build_semantic_finalize_messages(
                instruction=instruction,
                request=request,
                candidates=candidate_briefs,
                limit=limit,
            )
            content = self._client.chat_completions(messages)
            plan = parse_reorder_plan_from_response(content, known_ids)
            if plan.ordered_track_ids:
                final_ids = plan.ordered_track_ids[:limit]

        tracks = list(library.get_tracks_by_ids(final_ids))
        # Maintain order of final_ids
        id_to_track = {t.id: t for t in tracks}
        return [id_to_track[i] for i in final_ids if i in id_to_track]
    
    def llm_select_from_candidates(
        self,
        instruction: str,
        candidates: List[Track],
        limit: int,
    ) -> List[Track]:
        """
        Use LLM to select from a list of candidate tracks.
        
        Args:
            instruction: User instruction
            candidates: List of candidate tracks
            limit: Result count limit
            
        Returns:
            Refined list of tracks
        """
        candidate_briefs = [
            {
                "id": t.id,
                "title": t.title or "",
                "artist_name": getattr(t, "artist_name", "") or "",
                "album_name": getattr(t, "album_name", "") or "",
            }
            for t in candidates
        ]
        
        known_ids = {c["id"] for c in candidate_briefs}
        messages = build_semantic_finalize_messages(
            instruction=instruction,
            request=LibraryQueueRequest(),
            candidates=candidate_briefs,
            limit=limit,
        )
        
        try:
            content = self._client.chat_completions(messages)
            plan = parse_reorder_plan_from_response(content, known_ids)
            if plan.ordered_track_ids:
                id_to_track = {t.id: t for t in candidates}
                return [
                    id_to_track[tid] 
                    for tid in plan.ordered_track_ids[:limit] 
                    if tid in id_to_track
                ]
        except Exception as e:
            logger.warning("LLM selection failed: %s", e)
        
        # Fallback: return the first 'limit' tracks
        return candidates[:limit]