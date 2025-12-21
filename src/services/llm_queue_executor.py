"""
LLM Queue Executor Module

Responsible for executing queue reorder plans.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models.queue_plan import LLMQueueError, LibraryQueueRequest, QueueReorderPlan
from models.track import Track

logger = logging.getLogger(__name__)


class LLMQueueExecutor:
    """
    LLM Queue Executor
    
    Handles the execution and application of queue reorder plans.
    """
    
    def __init__(self):
        pass
    
    def apply_reorder_plan(
        self,
        player: Any,
        plan: QueueReorderPlan,
    ) -> Tuple[List[Track], int]:
        """
        Apply a reorder plan to the PlayerService.

        Args:
            player: PlayerService (duck typing: requires current_track, queue, set_queue)
            plan: QueueReorderPlan

        Returns:
            (new_queue, new_index)
        """
        if plan.clear_queue:
            if hasattr(player, "clear_queue"):
                player.clear_queue()
            else:
                player.set_queue([], 0)
            return [], -1
        if plan.library_request is not None:
            raise LLMQueueError("This plan contains a library_request; use apply_plan and provide a LibraryService.")

        current = getattr(player, "current_track", None)
        current_id = getattr(current, "id", None) if current else None
        queue: List[Track] = list(getattr(player, "queue", []))
        id_to_track = {t.id: t for t in queue}

        new_queue: List[Track] = []
        for track_id in plan.ordered_track_ids:
            track = id_to_track.get(track_id)
            if track:
                new_queue.append(track)

        # Append unmentioned tracks to the end (default behavior)
        for t in queue:
            if t.id not in set(plan.ordered_track_ids):
                new_queue.append(t)

        new_index = 0
        if current_id:
            for i, t in enumerate(new_queue):
                if t.id == current_id:
                    new_index = i
                    break

        player.set_queue(new_queue, new_index)
        return new_queue, new_index

    def apply_plan(
        self, 
        player: Any, 
        plan: QueueReorderPlan, 
        library: Any = None
    ) -> Tuple[List[Track], int]:
        """
        Apply a queue plan (supports clearing, fetching from library, and reordering the current queue).

        Args:
            player: PlayerService (duck typing: requires current_track, queue, set_queue, optionally clear_queue)
            plan: QueueReorderPlan
            library: LibraryService (duck typing: requires query_tracks)

        Returns:
            (new_queue, new_index)
        """
        current = getattr(player, "current_track", None)
        current_id = getattr(current, "id", None) if current else None
        queue: List[Track] = list(getattr(player, "queue", []))

        # clear_queue can be combined with subsequent library_request: stop/clear first, then set new queue.
        # Pure clear (with no other action) returns quickly to avoid redundant set_queue.
        if plan.clear_queue and plan.library_request is None and not plan.ordered_track_ids:
            if hasattr(player, "clear_queue"):
                player.clear_queue()
            else:
                player.set_queue([], 0)
            return [], -1

        new_queue, new_index = self.resolve_plan(
            plan=plan,
            queue=queue,
            current_track_id=current_id,
            library=library,
        )

        if plan.clear_queue and hasattr(player, "clear_queue"):
            player.clear_queue()

        player.set_queue(new_queue, new_index if new_queue else -1)
        return new_queue, new_index if new_queue else -1

    def resolve_plan(
        self,
        plan: QueueReorderPlan,
        queue: Sequence[Track],
        current_track_id: Optional[str] = None,
        library: Any = None,
    ) -> Tuple[List[Track], int]:
        """
        Resolve a plan into a specific queue without directly modifying PlayerService.

        - May query LibraryService
        - When semantic_fallback is enabled, may call LLM again for semantic filtering
        
        Note:
            Semantic filtering logic needs to be injected externally.
        """
        base_queue: List[Track] = list(queue)
        current_id = current_track_id

        if plan.clear_queue:
            base_queue = []
            current_id = None

        if plan.library_request is not None:
            if library is None or not hasattr(library, "query_tracks"):
                raise LLMQueueError("LibraryService missing (query_tracks required)")

            req = plan.library_request
            limit = int(req.limit) if isinstance(req.limit, int) else 30
            limit = max(1, min(200, limit))
            shuffle = bool(req.shuffle)
            tracks: List[Track] = list(
                library.query_tracks(
                    query=str(req.query or ""),
                    genre=str(req.genre or ""),
                    artist=str(req.artist or ""),
                    album=str(req.album or ""),
                    limit=limit,
                    shuffle=shuffle,
                )
            )
            
            # Semantic selection needs to be injected externally
            if not tracks:
                raise LLMQueueError(f"No tracks matching criteria found in library: {req.query or req.genre or req.artist or req.album or '(none specified)'}")

            mode = (req.mode or "replace").strip().lower()
            if mode not in {"replace", "append"}:
                mode = "replace"

            if mode == "replace":
                return tracks, 0 if tracks else -1

            seen = {t.id for t in base_queue}
            merged = base_queue + [t for t in tracks if t.id not in seen]

            new_index = 0
            if current_id:
                for i, t in enumerate(merged):
                    if t.id == current_id:
                        new_index = i
                        break
            return merged, new_index if merged else -1

        if plan.ordered_track_ids:
            id_to_track = {t.id: t for t in base_queue}
            ordered_ids = list(plan.ordered_track_ids)
            ordered_set = set(ordered_ids)

            new_queue: List[Track] = []
            for track_id in ordered_ids:
                track = id_to_track.get(track_id)
                if track:
                    new_queue.append(track)

            for t in base_queue:
                if t.id not in ordered_set:
                    new_queue.append(t)

            new_index = 0
            if current_id:
                for i, t in enumerate(new_queue):
                    if t.id == current_id:
                        new_index = i
                        break
            return new_queue, new_index if new_queue else -1

        # No-op: keep original queue.
        new_index = 0
        if current_id:
            for i, t in enumerate(base_queue):
                if t.id == current_id:
                    new_index = i
                    break
        return base_queue, new_index if base_queue else -1
    
    def resolve_plan_with_semantic_selector(
        self,
        plan: QueueReorderPlan,
        queue: Sequence[Track],
        current_track_id: Optional[str] = None,
        library: Any = None,
        semantic_selector: Any = None,
        tag_prefilter: Any = None,
    ) -> Tuple[List[Track], int]:
        """
        Resolve a plan into a specific queue (supporting semantic and tag pre-filtering).
        
        Args:
            plan: Queue reorder plan
            queue: Current queue
            current_track_id: ID of the currently playing track
            library: LibraryService
            semantic_selector: Semantic selector
            tag_prefilter: Tag pre-filter
            
        Returns:
            (new_queue, new_index)
        """
        base_queue: List[Track] = list(queue)
        current_id = current_track_id

        if plan.clear_queue:
            base_queue = []
            current_id = None

        if plan.library_request is not None:
            if library is None or not hasattr(library, "query_tracks"):
                raise LLMQueueError("LibraryService missing (query_tracks required)")

            req = plan.library_request
            limit = int(req.limit) if isinstance(req.limit, int) else 30
            limit = max(1, min(200, limit))
            shuffle = bool(req.shuffle)
            tracks: List[Track] = list(
                library.query_tracks(
                    query=str(req.query or ""),
                    genre=str(req.genre or ""),
                    artist=str(req.artist or ""),
                    album=str(req.album or ""),
                    limit=limit,
                    shuffle=shuffle,
                )
            )
            
            # If no direct filtering results, try semantic selection
            if not tracks and bool(req.semantic_fallback):
                # Try tag pre-filtering
                if tag_prefilter and hasattr(tag_prefilter, '__call__'):
                    try:
                        tracks = tag_prefilter(plan.instruction or "", library, limit)
                    except Exception as e:
                        logger.debug("Tag pre-filtering failed: %s", e)
                        tracks = []
                
                # If tag pre-filtering fails, fall back to semantic selection
                if not tracks and semantic_selector and hasattr(semantic_selector, '__call__'):
                    try:
                        tracks = semantic_selector(plan.instruction or "", library, req, limit)
                    except Exception as e:
                        logger.warning("Semantic selection failed: %s", e)
                        tracks = []

            if not tracks:
                q = req.genre or req.query or req.artist or req.album or "(none specified)"
                raise LLMQueueError(f"No tracks matching criteria found in library: {q}")

            mode = (req.mode or "replace").strip().lower()
            if mode not in {"replace", "append"}:
                mode = "replace"

            if mode == "replace":
                return tracks, 0 if tracks else -1

            seen = {t.id for t in base_queue}
            merged = base_queue + [t for t in tracks if t.id not in seen]

            new_index = 0
            if current_id:
                for i, t in enumerate(merged):
                    if t.id == current_id:
                        new_index = i
                        break
            return merged, new_index if merged else -1

        if plan.ordered_track_ids:
            id_to_track = {t.id: t for t in base_queue}
            ordered_ids = list(plan.ordered_track_ids)
            ordered_set = set(ordered_ids)

            new_queue: List[Track] = []
            for track_id in ordered_ids:
                track = id_to_track.get(track_id)
                if track:
                    new_queue.append(track)

            for t in base_queue:
                if t.id not in ordered_set:
                    new_queue.append(t)

            new_index = 0
            if current_id:
                for i, t in enumerate(new_queue):
                    if t.id == current_id:
                        new_index = i
                        break
            return new_queue, new_index if new_queue else -1

        # No-op: keep original queue.
        new_index = 0
        if current_id:
            for i, t in enumerate(base_queue):
                if t.id == current_id:
                    new_index = i
                    break
        return base_queue, new_index if base_queue else -1