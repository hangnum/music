"""
LLM Response Processing Utility Module

Provides shared functionality for LLM message building and response parsing.
Used by LLMQueueParser and LLMSemanticSelector to eliminate code duplication.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from models.queue_plan import LLMQueueError, LibraryQueueRequest, QueueReorderPlan
from services.llm_response_parser import strip_code_fences

logger = logging.getLogger(__name__)


def build_semantic_select_messages(
    instruction: str,
    request: LibraryQueueRequest,
    candidates: List[Dict[str, Any]],
    max_select: int,
    total_sent: int,
    total_limit: int,
) -> List[Dict[str, str]]:
    """
    Build semantic selection messages

    Args:
        instruction: User instruction
        request: Library request
        candidates: List of candidate tracks
        max_select: Maximum number of selections
        total_sent: Number of tracks already sent
        total_limit: Total limit

    Returns:
        Message list (for LLM API use)
    """
    payload = {
        "instruction": instruction,
        "library_request": {
            "query": request.query,
            "genre": request.genre,
            "artist": request.artist,
            "album": request.album,
            "limit": request.limit,
        },
        "note": f"Current batch is a slice of the music library (brief info for {total_sent}/{total_limit} tracks sent).",
        "max_select": max_select,
        "candidates": [
            {
                "id": str(r.get("id", "")),
                "title": str(r.get("title", "") or ""),
                "artist_name": str(r.get("artist_name", "") or ""),
                "album_name": str(r.get("album_name", "") or ""),
            }
            for r in candidates
            if r.get("id")
        ],
        "response_schema": {"selected_track_ids": ["<track_id>"], "reason": "Brief explanation (optional)"},
        "rules": [
            "Output JSON only (no markdown, no code blocks).",
            "selected_track_ids must come from candidates' ids.",
            f"Select at most {max_select} tracks; return empty list if none suitable in this batch.",
            "If user expresses style/mood (e.g., 'rock/relax/fast-paced'), infer based on title/artist/album clues (fuzzy matching allowed).",
        ],
    }

    system = (
        "You are a music library semantic filtering assistant for a local music player."
        "The user's library might not have genre tags; please make fuzzy inferences based on visible information to select candidate tracks."
        "Strictly output JSON according to the schema, and do not output anything other than JSON."
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def build_semantic_finalize_messages(
    instruction: str,
    request: LibraryQueueRequest,
    candidates: List[Dict[str, str]],
    limit: int,
) -> List[Dict[str, str]]:
    """
    Build semantic final selection messages

    Args:
        instruction: User instruction
        request: Library request
        candidates: List of candidate tracks
        limit: Result limit

    Returns:
        Message list (for LLM API use)
    """
    payload = {
        "instruction": instruction,
        "library_request": {
            "query": request.query,
            "genre": request.genre,
            "artist": request.artist,
            "album": request.album,
        },
        "limit": limit,
        "candidates": candidates,
        "response_schema": {"ordered_track_ids": ["<track_id>"], "reason": "Brief explanation (optional)"},
        "rules": [
            "Output JSON only (no markdown, no code blocks).",
            "ordered_track_ids can only use ids that appeared in candidates.",
            f"Return no more than {limit} ids, ordered by how well they match the request.",
        ],
    }

    system = (
        "You are making the final selection from the candidate track set."
        "Strictly output JSON according to the schema, and do not output anything other than JSON."
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def parse_selected_track_ids(content: str, known_ids: set[str]) -> List[str]:
    """
    Parse selected track IDs

    Args:
        content: Raw content returned by LLM
        known_ids: Set of known valid track IDs

    Returns:
        Filtered list of valid track IDs

    Raises:
        LLMQueueError: When parsing fails
    """
    raw = strip_code_fences(content).strip()
    try:
        data = json.loads(raw)
    except Exception as e:
        raise LLMQueueError(f"LLM returned non-JSON: {raw[:200]}") from e

    ids = data.get("selected_track_ids", [])
    if not isinstance(ids, list):
        return []

    out: List[str] = []
    seen = set()
    for v in ids:
        if not isinstance(v, str):
            continue
        if v in known_ids and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def parse_reorder_plan_from_response(content: str, known_ids: set[str]) -> QueueReorderPlan:
    """
    Parse reorder plan from LLM response

    This is a general parsing function for handling responses containing ordered_track_ids.

    Args:
        content: Raw content returned by LLM
        known_ids: Set of known valid track IDs

    Returns:
        QueueReorderPlan object

    Raises:
        LLMQueueError: When parsing fails
    """
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
