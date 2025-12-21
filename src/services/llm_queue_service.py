"""
LLM Play Queue Management Service

Manages play queue dynamically through LLM calls (supports multiple providers),
e.g.: Reorder, deduplicate, truncate queue based on natural language instructions.

Refactored to facade pattern, coordinating the following sub-modules:
- LLMQueueParser: LLM message construction and response parsing
- LLMQueueExecutor: Plan execution and queue operations
- LLMSemanticSelector: Semantic selection functionality
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING
import logging
import threading

from services.config_service import ConfigService
from models.track import Track
from models.queue_plan import LLMQueueError, QueueReorderPlan

from .llm_queue_parser import LLMQueueParser
from .llm_queue_executor import LLMQueueExecutor
from .llm_semantic_selector import LLMSemanticSelector

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.tag_service import TagService

logger = logging.getLogger(__name__)


class LLMQueueService:
    """
    Converts natural language instructions to queue change plans and applies to player queue.

    Coordinates sub-modules to provide unified service interface.
    
    Supports multiple LLM providers (SiliconFlow, Gemini, etc.).
    """

    def __init__(
        self,
        config: Optional[ConfigService] = None,
        client: Optional["LLMProvider"] = None,
        tag_service: Optional["TagService"] = None,
    ):
        """Initialize LLM queue service
        
        Args:
            config: Configuration service instance
            client: LLM provider instance (optional, created based on config by default)
            tag_service: Tag service instance (optional, used for tag pre-filtering)
        """
        self._config = config or ConfigService()
        self._tag_service = tag_service
        
        if client is not None:
            self._client = client
        else:
            from services.llm_providers import create_llm_provider
            self._client = create_llm_provider(self._config)
        
        # Initialize sub-modules
        self._parser = LLMQueueParser()
        self._executor = LLMQueueExecutor()
        self._semantic_selector = LLMSemanticSelector(self._client, self._config)
        
        # Tag query parser (lazy-loaded) and its thread lock
        self._tag_query_parser: Optional[Any] = None
        self._tag_query_parser_lock = threading.Lock()

    def suggest_reorder(
        self,
        instruction: str,
        queue: Sequence[Track],
        current_track_id: Optional[str] = None,
        library_context: Optional[Dict[str, Any]] = None,
    ) -> QueueReorderPlan:
        """Generate queue reordering plan"""
        max_items = int(self._config.get("llm.queue_manager.max_items", 50))
        items = list(queue)[: max(0, max_items)]

        known_ids = {t.id for t in items}
        if current_track_id and current_track_id not in known_ids:
            current_track_id = None

        messages = self._parser.build_reorder_messages(instruction, items, current_track_id, library_context)
        content = self._client.chat_completions(messages)
        plan = self._parser.parse_reorder_plan(content, known_ids)
        plan = replace(plan, instruction=instruction)

        if plan.clear_queue:
            return plan
        if plan.library_request is not None:
            return plan

        # Fallback: if LLM returns empty list or no valid IDs, make no changes
        if not plan.ordered_track_ids:
            return QueueReorderPlan([t.id for t in items], reason="LLM did not provide a valid queue, keeping original order")
        
        return plan


    def suggest_and_apply_reorder(self, player: Any, instruction: str) -> QueueReorderPlan:
        """Convenience method: generate a reorder plan based on the current player queue and apply it immediately."""
        queue = list(getattr(player, "queue", []))
        current = getattr(player, "current_track", None)
        current_id = getattr(current, "id", None) if current else None
        
        plan = self.suggest_reorder(instruction=instruction, queue=queue, current_track_id=current_id)
        self.apply_reorder_plan(player, plan)
        return plan
    
    def apply_reorder_plan(
        self,
        player: Any,
        plan: QueueReorderPlan,
    ) -> Tuple[List[Track], int]:
        """Apply a reorder plan to the PlayerService."""
        return self._executor.apply_reorder_plan(player, plan)
    
    def apply_plan(
        self,
        player: Any,
        plan: QueueReorderPlan,
        library: Any = None,
    ) -> Tuple[List[Track], int]:
        """Apply a queue plan (supports clearing, fetching from library, and reordering the current queue)."""
        current = getattr(player, "current_track", None)
        current_id = getattr(current, "id", None) if current else None
        queue = list(getattr(player, "queue", []))
        
        # Use the resolve_plan method which integrates semantic filtering.
        new_queue, new_index = self.resolve_plan(plan, queue, current_id, library)
        
        # Apply queue changes to the player.
        if plan.clear_queue and hasattr(player, "clear_queue"):
            player.clear_queue()
        
        player.set_queue(new_queue, new_index if new_queue else -1)
        return new_queue, new_index
    
    def resolve_plan(
        self,
        plan: QueueReorderPlan,
        queue: Sequence[Track],
        current_track_id: Optional[str] = None,
        library: Any = None,
    ) -> Tuple[List[Track], int]:
        """
        Resolve a plan into a specific queue without directly modifying PlayerService.
        
        - May query LibraryService.
        - When semantic_fallback is enabled, may call LLM again for semantic filtering.
        """
        return self._executor.resolve_plan_with_semantic_selector(
            plan=plan,
            queue=queue,
            current_track_id=current_track_id,
            library=library,
            semantic_selector=self._semantic_selector.semantic_select_tracks_from_library,
            tag_prefilter=self._try_tag_prefilter,
        )
        
    def _try_tag_prefilter(
        self,
        instruction: str,
        library: Any,
        limit: int,
    ) -> List[Track]:
        """
        Attempt to get candidate tracks using tag pre-filtering.
        
        Two-stage optimization:
        1. Resolve user instruction into a tag query.
        2. Pre-filter tracks using the tag query.
        
        Args:
            instruction: User's natural language instruction.
            library: LibraryService instance.
            limit: Result count limit.
            
        Returns:
            List of candidate tracks, or an empty list if pre-filtering fails.
        """
        if not self._tag_service:
            logger.debug("TagService not initialized, skipping tag pre-filtering")
            return []
        
        # Check if there are enough LLM tags.
        llm_tags = self._tag_service.get_all_tag_names(source="llm")
        if len(llm_tags) < 5:
            logger.debug("Insufficient LLM tags (%d), skipping tag pre-filtering", len(llm_tags))
            return []
        
        # Initialize TagQueryParser (lazy-loaded with thread safety).
        if self._tag_query_parser is None:
            with self._tag_query_parser_lock:
                if self._tag_query_parser is None:
                    from services.tag_query_parser import TagQueryParser
                    self._tag_query_parser = TagQueryParser(
                        client=self._client,
                        tag_service=self._tag_service,
                    )
        
        # Resolve instruction into a tag query.
        try:
            tag_query = self._tag_query_parser.parse(instruction, llm_tags)
        except Exception as e:
            logger.warning("Tag query resolution failed: %s", e)
            return []
        
        if not tag_query.is_valid:
            logger.debug("No valid tags matched: %s", tag_query.reason)
            return []
        
        if tag_query.confidence < 0.5:
            logger.debug("Tag matching confidence too low (%.2f), skipping pre-filtering", tag_query.confidence)
            return []
        
        logger.info(
            "Tag pre-filtering: matched tags=%s, mode=%s, confidence=%.2f",
            tag_query.tags, tag_query.match_mode, tag_query.confidence
        )
        
        # Query tracks by tags.
        track_ids = self._tag_service.get_tracks_by_tags(
            tag_names=tag_query.tags,
            match_mode=tag_query.match_mode,
            limit=limit * 2,  # Fetch more for subsequent refinement.
        )
        
        if not track_ids:
            logger.debug("Tag query returned no results")
            return []
        
        # Get track details.
        if not hasattr(library, "get_tracks_by_ids"):
            return []
        
        tracks = list(library.get_tracks_by_ids(track_ids))
        
        if len(tracks) <= limit:
            return tracks
        
        # If too many results, use LLM to refine.
        return self._semantic_selector.llm_select_from_candidates(
            instruction=instruction,
            candidates=tracks,
            limit=limit,
        )
        
    @property
    def client(self) -> Any:
        """Get LLM client."""
        return self._client
    
    @property
    def parser(self) -> LLMQueueParser:
        """Get parser."""
        return self._parser
    
    @property
    def executor(self) -> LLMQueueExecutor:
        """Get executor."""
        return self._executor
    
    @property
    def semantic_selector(self) -> LLMSemanticSelector:
        """Get semantic selector."""
        return self._semantic_selector
