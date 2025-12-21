"""
Daily Playlist Service

Generates today's playlist based on user input tags, supports three-tier filtering strategy:
1. Direct tag matching
2. LLM semantic expansion
3. Random supplement
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.library_service import LibraryService
    from services.tag_service import TagService

from models.track import Track

logger = logging.getLogger(__name__)


@dataclass
class DailyPlaylistResult:
    """Daily playlist generation result"""
    
    tracks: List[Track] = field(default_factory=list)
    matched_by_tags: int = 0          # Number of tracks matched by direct tag matching
    matched_by_semantic: int = 0      # Number of tracks matched by semantic expansion
    filled_random: int = 0            # Number of tracks filled by random supplement
    expanded_tags: List[str] = field(default_factory=list)  # List of LLM-expanded tags
    input_tags: List[str] = field(default_factory=list)     # Original tags input by user
    
    @property
    def total(self) -> int:
        """Return total number of tracks in playlist"""
        return len(self.tracks)
    
    @property
    def summary(self) -> str:
        """Return generation result summary"""
        parts = []
        if self.matched_by_tags > 0:
            parts.append(f"Tag match {self.matched_by_tags} tracks")
        if self.matched_by_semantic > 0:
            parts.append(f"Semantic expansion {self.matched_by_semantic} tracks")
        if self.filled_random > 0:
            parts.append(f"Random supplement {self.filled_random} tracks")
        return " / ".join(parts) if parts else "No matching results"


class DailyPlaylistService:
    """
    Daily playlist generation service
    
    Generates today's playlist using three-tier filtering strategy:
    1. Directly filter tracks using user-provided tags
    2. If not enough, call LLM to expand with semantically similar tags
    3. If still not enough, supplement with random tracks from the library
    
    Usage example:
        service = DailyPlaylistService(tag_service, library_service, llm_provider)
        result = service.generate(["Pop", "Relax"], limit=50)
        print(f"Generated {result.total} tracks: {result.summary}")
    """
    
    def __init__(
        self,
        tag_service: "TagService",
        library_service: "LibraryService",
        llm_provider: Optional["LLMProvider"] = None,
    ):
        """
        Initialize Daily Playlist Service
        
        Args:
            tag_service: Tag service instance
            library_service: Library service instance
            llm_provider: LLM provider instance (optional, used for semantic expansion)
        """
        self._tag_service = tag_service
        self._library_service = library_service
        self._llm_provider = llm_provider
    
    def generate(
        self,
        input_tags: List[str],
        limit: int = 50,
        shuffle: bool = True,
    ) -> DailyPlaylistResult:
        """
        Generate daily playlist
        
        Args:
            input_tags: List of tags input by user
            limit: Target number of tracks (default 50)
            shuffle: Whether to shuffle the order (default True)
            
        Returns:
            DailyPlaylistResult containing generated tracks and statistics
        """
        result = DailyPlaylistResult(input_tags=list(input_tags))
        collected: List[Track] = []
        collected_ids: set[str] = set()
        
        # Clean up input tags
        input_tags = [t.strip() for t in input_tags if t.strip()]
        
        if not input_tags:
            logger.warning("No valid tags provided, using random supplement directly")
        else:
            # Step 1: Direct tag matching
            logger.info("Step 1: Direct tag matching, tags: %s", input_tags)
            track_ids = self._tag_service.get_tracks_by_tags(
                input_tags, match_mode="any", limit=limit
            )
            
            if track_ids:
                tracks = self._library_service.get_tracks_by_ids(track_ids)
                for track in tracks:
                    if track.id not in collected_ids:
                        collected.append(track)
                        collected_ids.add(track.id)
                result.matched_by_tags = len(collected)
                logger.info("Direct tag matching found %d tracks", result.matched_by_tags)
            
            # Step 2: LLM semantic expansion
            if len(collected) < limit and self._llm_provider:
                logger.info("Step 2: LLM semantic expansion")
                remaining = limit - len(collected)
                expanded_tags = self._expand_tags_with_llm(input_tags)
                result.expanded_tags = expanded_tags
                
                # Filter out already used tags
                new_tags = [t for t in expanded_tags if t.lower() not in 
                           {tag.lower() for tag in input_tags}]
                
                if new_tags:
                    logger.info("LLM expanded %d new tags: %s", len(new_tags), new_tags)
                    more_ids = self._tag_service.get_tracks_by_tags(
                        new_tags, match_mode="any", limit=remaining * 2
                    )
                    
                    if more_ids:
                        more_tracks = self._library_service.get_tracks_by_ids(more_ids)
                        semantic_count = 0
                        for track in more_tracks:
                            if track.id not in collected_ids:
                                collected.append(track)
                                collected_ids.add(track.id)
                                semantic_count += 1
                                if len(collected) >= limit:
                                    break
                        result.matched_by_semantic = semantic_count
                        logger.info("Semantic expansion found %d new tracks", semantic_count)
                else:
                    logger.info("LLM did not expand any new tags")
        
        # Step 3: Random supplement
        if len(collected) < limit:
            remaining = limit - len(collected)
            logger.info("Step 3: Random supplement %d tracks", remaining)
            
            # Get more tracks for deduplication
            random_tracks = self._library_service.query_tracks(
                limit=remaining * 3, shuffle=True
            )
            
            random_count = 0
            for track in random_tracks:
                if track.id not in collected_ids:
                    collected.append(track)
                    collected_ids.add(track.id)
                    random_count += 1
                    if len(collected) >= limit:
                        break
            
            result.filled_random = random_count
            logger.info("Randomly supplemented %d tracks", random_count)
        
        # Shuffle order
        if shuffle and len(collected) > 1:
            random.shuffle(collected)
        
        result.tracks = collected
        logger.info("Daily playlist generation completed: %s", result.summary)
        
        return result
    
    def _expand_tags_with_llm(self, input_tags: List[str]) -> List[str]:
        """
        Use LLM to expand semantically similar tags
        
        Args:
            input_tags: List of tags input by user
            
        Returns:
            Expanded tag list (contains original tags and semantically similar ones)
        """
        if not self._llm_provider:
            return []
        
        # Get all available tags
        all_tags = self._tag_service.get_all_tag_names()
        if not all_tags:
            logger.debug("No available tags for expansion")
            return []
        
        # Limit the number of tags sent to LLM
        max_tags = 500
        tags_sample = all_tags[:max_tags]
        
        messages = self._build_expand_messages(input_tags, tags_sample)
        
        try:
            content = self._llm_provider.chat_completions(messages)
            return self._parse_expand_response(content, set(all_tags))
        except Exception as e:
            logger.warning("LLM tag expansion failed: %s", e)
            return []
    
    def _build_expand_messages(
        self,
        input_tags: List[str],
        available_tags: List[str],
    ) -> List[Dict[str, str]]:
        """Build LLM tag expansion request message"""
        payload = {
            "task": "expand_music_tags",
            "user_tags": input_tags,
            "available_tags": available_tags,
            "note": f"Total {len(available_tags)} tags available",
            "response_schema": {
                "expanded_tags": ["tag1", "tag2", "..."],
                "reason": "Brief explanation for the expansion",
            },
            "rules": [
                "Only output JSON (no markdown, no code blocks).",
                "expanded_tags must come from available_tags (case-insensitive).",
                "Find tags that are semantically close, style-similar, or often appear together with user_tags.",
                "Return the 10-20 most relevant tags.",
                "Can include original tags from user_tags.",
            ],
        }
        
        system = (
            "You are a music tag expansion assistant. Based on user-provided tags, "
            "find semantically close or style-similar tags from the available list "
            "to help users discover more music they might like. "
            "Strictly output JSON according to the schema, and do not output anything other than JSON."
        )
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def _parse_expand_response(
        self,
        content: str,
        available_tags_set: set,
    ) -> List[str]:
        """Parse LLM expansion response"""
        raw = self._strip_code_fences(content).strip()
        
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning("LLM returned non-JSON: %s", raw[:200])
            return []
        
        # Extract expanded tags
        expanded = data.get("expanded_tags", [])
        if not isinstance(expanded, list):
            expanded = []
        
        # Case-insensitive matching
        available_lower = {t.lower(): t for t in available_tags_set}
        valid_tags = []
        for tag in expanded:
            if isinstance(tag, str):
                tag_lower = tag.strip().lower()
                if tag_lower in available_lower:
                    valid_tags.append(available_lower[tag_lower])
        
        return valid_tags
    
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove code block markers"""
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                return "\n".join(lines[1:-1])
        return t
