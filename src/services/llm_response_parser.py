"""
LLM Response Parsing Utilities Module

Provides shared parsing functionality for LLM responses:
- Removing code block formatting
- JSON parsing with automatic recovery
- Track ID extraction
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional, Set


logger = logging.getLogger(__name__)


class LLMParseError(RuntimeError):
    """LLM response parsing error"""
    pass


def strip_code_fences(text: str) -> str:
    """
    Remove various code block formats.
    
    Handles:
    - ```json\\n...\\n```
    - ```\\n...\\n```
    - `...`
    - Surrounding whitespace
    
    Args:
        text: Original text
        
    Returns:
        Text after removing code blocks
    """
    t = text.strip()
    
    # Handle ```...``` format (optionally with language identifier)
    if t.startswith("```"):
        lines = t.splitlines()
        if len(lines) >= 2:
            # Find the ending ```
            end_idx = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip().startswith("```"):
                    end_idx = i
                    break
            # Remove first and last line
            return "\n".join(lines[1:end_idx]).strip()
    
    # Handle single backticks `{...}`
    if t.startswith("`") and t.endswith("`") and not t.startswith("```"):
        return t[1:-1].strip()
    
    return t


def try_parse_json(
    text: str,
    raise_on_error: bool = True,
) -> Optional[dict]:
    """
    Attempt to parse JSON with multiple recovery strategies.
    
    Parsing sequence:
    1. Direct parse
    2. Parse after stripping code blocks
    3. Regex extraction of JSON object
    4. Repair common formatting issues (e.g., trailing commas)
    
    Args:
        text: Text to parse
        raise_on_error: Whether to raise an exception on failure
        
    Returns:
        Parsed dictionary, or None/exception on failure
        
    Raises:
        LLMParseError: When raise_on_error=True and parsing fails
    """
    # Strategy 1: Direct parse
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Strip code blocks and parse
    raw = strip_code_fences(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Regex extraction of JSON object
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        extracted = match.group()
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            # Strategy 4: Fix trailing comma issue
            fixed = re.sub(r',(\s*[}\]])', r'\1', extracted)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
    
    # All strategies failed
    logger.warning("LLM returned unparseable content: %s", raw[:200])
    if raise_on_error:
        raise LLMParseError(f"LLM returned non-JSON content: {raw[:200]}")
    return None


def parse_track_ids_from_content(
    content: str,
    known_ids: Set[str],
    id_field: str = "track_ids",
) -> List[str]:
    """
    Extract a list of Track IDs from an LLM response.
    
    Args:
        content: LLM response content
        known_ids: Set of known valid IDs
        id_field: Field name for IDs in the JSON
        
    Returns:
        List of valid Track IDs
    """
    data = try_parse_json(content, raise_on_error=False)
    if not data:
        return []
    
    # Try multiple field names
    ids = data.get(id_field) or data.get("selected_ids") or []
    
    if not isinstance(ids, list):
        return []
    
    # Filter for valid IDs
    result = []
    for track_id in ids:
        if isinstance(track_id, str) and track_id in known_ids:
            result.append(track_id)
    
    return result


def parse_tags_from_content(
    content: str,
    known_ids: Set[str],
    tags_field: str = "tags",
    max_tag_length: int = 50,
) -> Dict[str, List[str]]:
    """
    Extract a dictionary of tags from an LLM response.
    
    Args:
        content: LLM response content
        known_ids: Set of known valid Track IDs
        tags_field: Field name for tags in the JSON
        max_tag_length: Maximum length for a single tag
        
    Returns:
        Dictionary mapping track_id to a list of tags
    """
    data = try_parse_json(content, raise_on_error=False)
    if not data:
        return {}
    
    tags_data = data.get(tags_field, {})
    if not isinstance(tags_data, dict):
        return {}
    
    result: Dict[str, List[str]] = {}
    for track_id, tags in tags_data.items():
        if track_id not in known_ids:
            continue
        if not isinstance(tags, list):
            continue
        
        # Filter for valid tags
        valid_tags = []
        for tag in tags:
            if isinstance(tag, str):
                tag = tag.strip()
                if tag and len(tag) <= max_tag_length:
                    valid_tags.append(tag)
        
        if valid_tags:
            result[track_id] = valid_tags
    
    return result
