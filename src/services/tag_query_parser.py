"""
Tag Query Parser

Parses user's natural language instructions into tag query conditions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.tag_service import TagService

logger = logging.getLogger(__name__)


@dataclass
class TagQuery:
    """Tag query result"""
    tags: List[str] = field(default_factory=list)
    match_mode: str = "any"  # "any" | "all"
    confidence: float = 0.0  # 0.0 - 1.0
    reason: str = ""
    
    @property
    def is_valid(self) -> bool:
        """Whether the query is valid (has matching tags)."""
        return len(self.tags) > 0


class TagQueryParser:
    """
    Parses natural language into tag query conditions.
    
    Example:
        parser = TagQueryParser(client, tag_service)
        
        query = parser.parse("I want to hear Jay Chou's songs", available_tags)
        # -> TagQuery(tags=["Jay Chou"], match_mode="any", confidence=0.9)
        
        query = parser.parse("Relaxing classical music", available_tags)
        # -> TagQuery(tags=["Classical", "Relaxing"], match_mode="all", confidence=0.8)
    """
    
    def __init__(
        self,
        client: "LLMProvider",
        tag_service: Optional["TagService"] = None,
    ):
        """
        Initialize the parser.
        
        Args:
            client: LLM provider
            tag_service: Tag service (optional, used to fetch available tags)
        """
        self._client = client
        self._tag_service = tag_service
    
    def parse(
        self,
        instruction: str,
        available_tags: Optional[List[str]] = None,
    ) -> TagQuery:
        """
        Parse natural language instruction into a tag query.
        
        Args:
            instruction: User's natural language instruction
            available_tags: List of available tags (if None, fetched from TagService)
            
        Returns:
            TagQuery object
        """
        if not instruction.strip():
            return TagQuery()
        
        # Get available tags
        if available_tags is None:
            if self._tag_service:
                available_tags = self._tag_service.get_all_tag_names()
            else:
                available_tags = []
        
        if not available_tags:
            logger.debug("No available tags, returning empty query")
            return TagQuery(reason="No available tags")
        
        messages = self._build_parse_messages(instruction, available_tags)
        
        try:
            content = self._client.chat_completions(messages)
            return self._parse_response(content, set(available_tags))
        except Exception as e:
            logger.warning("Failed to parse tag query: %s", e)
            return TagQuery(reason=f"Parsing failed: {e}")
    
    def _build_parse_messages(
        self,
        instruction: str,
        available_tags: List[str],
    ) -> List[Dict[str, str]]:
        """Build parsing request messages."""
        # Limit the number of available tags to avoid excessive token usage
        max_tags = 500
        tags_sample = available_tags[:max_tags]
        
        payload = {
            "task": "parse_music_query",
            "instruction": instruction,
            "available_tags": tags_sample,
            "note": f"Total {len(available_tags)} tags available" + (
                f", showing the first {max_tags}" if len(available_tags) > max_tags else ""
            ),
            "response_schema": {
                "matched_tags": ["tag1", "tag2"],
                "match_mode": "any|all",
                "confidence": 0.8,
                "reason": "short explanation",
            },
            "rules": [
                "Only output pure JSON (no markdown, no code blocks).",
                "matched_tags must come from available_tags (case-insensitive).",
                "If the instruction implies all conditions must be met, use match_mode='all'.",
                "If the instruction implies any condition is enough, use match_mode='any'.",
                "confidence represents the matching confidence (0.0-1.0).",
                "If no tags can be matched, return an empty matched_tags list.",
            ],
        }
        
        system = (
            "You are a music query parsing assistant. Based on the user's natural language instruction, "
            "find the most relevant tags from the available list. "
            "Strictly output JSON according to the schema, and do not output anything other than JSON."
        )
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def _parse_response(
        self,
        content: str,
        available_tags_set: set,
    ) -> TagQuery:
        """Parse LLM response."""
        raw = self._strip_code_fences(content).strip()
        
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning("LLM returned non-JSON: %s", raw[:200])
            return TagQuery(reason=f"LLM returned non-JSON: {raw[:200]}")
        
        # Extract matched tags
        matched = data.get("matched_tags", [])
        if not isinstance(matched, list):
            matched = []
        
        # Case-insensitive matching
        available_lower = {t.lower(): t for t in available_tags_set}
        valid_tags = []
        for tag in matched:
            if isinstance(tag, str):
                tag_lower = tag.strip().lower()
                if tag_lower in available_lower:
                    valid_tags.append(available_lower[tag_lower])
        
        # Extract match mode
        match_mode = data.get("match_mode", "any")
        if match_mode not in {"any", "all"}:
            match_mode = "any"
        
        # Extract confidence
        confidence = data.get("confidence", 0.0)
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.0
        
        reason = data.get("reason", "")
        if not isinstance(reason, str):
            reason = ""
        
        return TagQuery(
            tags=valid_tags,
            match_mode=match_mode,
            confidence=confidence,
            reason=reason,
        )
    
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove code block markers."""
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                return "\n".join(lines[1:-1])
        return t
