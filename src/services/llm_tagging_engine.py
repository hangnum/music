
"""
LLM Tagging Engine Module

Responsible for constructing LLM messages and parsing tagging responses.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from services.llm_response_parser import (
    strip_code_fences,
    parse_tags_from_content,
    LLMParseError,
)
from models.llm_tagging import LLMTaggingError

logger = logging.getLogger(__name__)


class LLMTaggingEngine:
    """
    LLM Tagging Engine
    
    Handles the LLM interaction logic for tag generation.
    """

    
    def __init__(
        self,
        client: Any,
        config: Any,
        web_search: Optional[Any] = None,
    ):
        """
        Initialize the tagging engine.
        
        Args:
            client: LLM provider
            config: Configuration service
            web_search: Web search service
        """
        self._client = client
        self._config = config
        self._web_search = web_search
        
        # Read batch parameters from configuration
        raw_batch_size = config.get("llm.tagging.batch_request_size", 12)
        self._batch_request_size = max(1, min(50, int(raw_batch_size)))
        
        raw_batch_size_ws = config.get(
            "llm.tagging.batch_request_size_with_web_search", 6
        )
        self._batch_request_size_with_web_search = max(1, min(20, int(raw_batch_size_ws)))
        
        raw_delay = config.get("llm.tagging.batch_delay_seconds", 0.5)
        self._batch_delay_seconds = max(0.0, min(10.0, float(raw_delay)))
        
        raw_retries = config.get("llm.tagging.max_retries", 3)
        self._max_retries = max(0, min(10, int(raw_retries)))
    
    def request_tags_for_batch(
        self,
        tracks: List[Any],
        tags_per_track: int,
        use_web_search: bool = False,
    ) -> Dict[str, List[str]]:
        """
        Request tags for a batch of tracks.
        
        Args:
            tracks: List of tracks
            tags_per_track: Maximum tags per track
            use_web_search: Whether to enhance tagging with web search
            
        Returns:
            Dictionary mapping track IDs to a list of tags.
        """
        result: Dict[str, List[str]] = {}
        if not tracks:
            return result

        max_request_tracks = (
            self._batch_request_size_with_web_search 
            if use_web_search 
            else self._batch_request_size
        )

        for start in range(0, len(tracks), max_request_tracks):
            batch = tracks[start:start + max_request_tracks]
            track_briefs: List[Dict[str, str]] = []
            known_ids = set()

            for track in batch:
                artist = getattr(track, "artist_name", "") or ""
                title = track.title or ""
                album = getattr(track, "album_name", "") or ""
                genre = getattr(track, "genre", "") or ""

                brief: Dict[str, str] = {
                    "id": track.id,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "genre": genre,
                }
                known_ids.add(track.id)

                if use_web_search and self._web_search:
                    try:
                        search_context = self._web_search.get_music_context(
                            artist=artist,
                            title=title,
                            album=album,
                            max_total_chars=300,
                        )
                        if search_context:
                            brief["web_context"] = search_context
                    except Exception as e:
                        logger.warning(
                            "Batch tagging search failed (track %s): %s",
                            track.id,
                            e,
                        )

                track_briefs.append(brief)

            messages = self.build_tagging_messages(
                track_briefs,
                tags_per_track,
                use_web_search,
            )

            content = None
            for retry in range(self._max_retries):
                try:
                    content = self._client.chat_completions(messages)
                    break
                except Exception as e:
                    if retry < self._max_retries - 1:
                        wait_time = 2 * (retry + 1)
                        logger.warning(
                            "Batch LLM call failed (retry %d): %s; waiting %d sec",
                            retry + 1,
                            e,
                            wait_time,
                        )
                        time.sleep(wait_time)
                    else:
                        logger.warning("Batch LLM call failed, skipping batch: %s", e)

            if not content:
                continue

            batch_result = self.parse_tagging_response(content, known_ids)
            if not batch_result:
                logger.warning(
                    "Batch LLM returned empty/invalid result: tracks=%d",
                    len(batch),
                )
            result.update(batch_result)

            time.sleep(self._batch_delay_seconds)

        return result
    
    def build_tagging_messages(
        self,
        tracks: List[Dict[str, str]],
        tags_per_track: int,
        use_web_search: bool = False,
    ) -> List[Dict[str, str]]:
        """Build tagging request messages."""
        # Build example output
        example_output = '{"tags": {"track_id_1": ["Pop", "Mandarin", "Jay Chou"], "track_id_2": ["Rock", "English"]}}'
        
        payload = {
            "task": "music_tagging",
            "tracks": tracks,
            "max_tags_per_track": tags_per_track,
            "tag_categories": [
                "Artist/Singer name",
                "Music style/genre (e.g., Rock, Pop, Classical, Electronic, Jazz, Hip-Hop, R&B, Folk, etc.)",
                "Mood/Atmosphere (e.g., Relaxing, Energetic, Sad, Happy, Romantic, etc.)",
                "Era/Period (e.g., 80s, 90s, Classic, Modern, etc.)",
                "Language (e.g., Chinese, English, Japanese, Korean, etc.)",
                "Other characteristics (e.g., Instrumental, Live, Cover, etc.)",
            ],
            "response_format": {
                "type": "json_object",
                "schema": {"tags": {"<track_id>": ["tag1", "tag2"]}},
                "example": example_output,
            },
            "rules": [
                "[IMPORTANT] Output pure JSON only, without any markdown code blocks (NO ```).",
                "[IMPORTANT] Output must be valid JSON, ensuring quotes are matched and no trailing commas exist.",
                f"Generate 1-{tags_per_track} tags per track.",
                "Tags should be concise (2-10 words) and descriptive.",
                "Omit categories if you cannot determine a suitable tag.",
                "Prefer English tags for common styles (e.g., Rock, Pop, R&B).",
            ],
        }
        
        # Adjust system prompt based on web search availability
        base_instruction = (
            "You are a professional music tagging assistant. Your task is to generate accurate descriptive tags for music tracks.\n\n"
            "【Output Format Requirements】\n"
            "- Output pure JSON object only\n"
            "- Prohibit the use of markdown code blocks (do not write ```)\n"
            "- Prohibit adding any explanatory text outside the JSON\n\n"
            f"【Output Example】\n{example_output}"
        )
        
        if use_web_search:
            system = (
                f"{base_instruction}\n\n"
                "【Data Source】\n"
                "You will receive song titles, artists, album info, and context from web searches (web_context)."
                "Please synthesize this info to generate accurate tags."
            )
        else:
            system = (
                f"{base_instruction}\n\n"
                "【Data Source】\n"
                "Generate tags based on song title, artist, album, and genre info."
            )
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def parse_tagging_response(
        self,
        content: str,
        known_ids: set,
    ) -> Dict[str, List[str]]:
        """Parse LLM tagging response."""
        try:
            return parse_tags_from_content(content, known_ids)
        except LLMParseError as e:
            raise LLMTaggingError(str(e)) from e
    
    def retry_tracks_individually(
        self,
        tracks: List[Any],
        tags_per_track: int,
        use_web_search: bool = False,
    ) -> Dict[str, List[str]]:
        """
        Retry tracks in a batch individually.
        
        Called when batch processing fails, attempting to request tags for each track separately.
        
        Args:
            tracks: List of tracks to retry
            tags_per_track: Maximum tags per track
            use_web_search: Whether to enhance with web search
            
        Returns:
            Dictionary of successfully tagged track IDs and their tags.
        """
        result: Dict[str, List[str]] = {}
        failed_count = 0
        
        for track in tracks:
            try:
                # Call batch method for a single track (batch size 1)
                single_result = self.request_tags_for_batch(
                    [track], tags_per_track, use_web_search
                )
                result.update(single_result)
            except Exception as e:
                failed_count += 1
                track_id = getattr(track, 'id', 'unknown')
                logger.warning(
                    "Per-track retry failed for track %s: %s",
                    track_id, e
                )
                # Continue to the next track on failure
                continue
            
            # Short delay between tracks to avoid excessive API call frequency
            time.sleep(self._batch_delay_seconds * 0.5)
        
        if failed_count > 0:
            logger.info(
                "Per-track retry completed: %d/%d succeeded",
                len(tracks) - failed_count, len(tracks)
            )
        
        return result
    
    def tag_single_track_detailed(
        self,
        track: Any,
        use_web_search: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform detailed tagging for a single track.
        
        Uses web search for in-depth info, then calls LLM to generate high-quality tags.
        
        Args:
            track: Track object
            use_web_search: Whether to use web search
            
        Returns:
            Tagging result.
        """
        artist = getattr(track, "artist_name", "") or ""
        title = track.title or ""
        album = getattr(track, "album_name", "") or ""
        genre = getattr(track, "genre", "") or ""
        
        # Get detailed search context
        search_results = []
        if use_web_search and self._web_search:
            try:
                # Search for song info
                song_info = self._web_search.search_music_info(
                    artist=artist, title=title, max_results=5
                )
                search_results.extend(song_info)
                
                # Search for artist info
                if artist:
                    artist_info = self._web_search.search_artist_info(
                        artist=artist, max_results=3
                    )
                    search_results.extend(artist_info)
                
                # Search for album info
                if album:
                    album_info = self._web_search.search_album_info(
                        artist=artist, album=album, max_results=2
                    )
                    search_results.extend(album_info)
            except Exception as e:
                logger.warning("Detailed tagging search failed: %s", e)
        
        search_context = " | ".join(search_results[:10]) if search_results else ""
        
        # Build detailed tagging request
        messages = self.build_detailed_tagging_messages(
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            search_context=search_context,
        )
        
        try:
            content = self._client.chat_completions(messages)
            result = self.parse_detailed_response(content)
        except Exception as e:
            logger.error("Detailed tagging LLM call failed: %s", e)
            return {
                "tags": [],
                "search_context": search_context,
                "analysis": f"Tagging failed: {e}",
            }
        
        result["search_context"] = search_context
        return result
    
    def build_detailed_tagging_messages(
        self,
        title: str,
        artist: str,
        album: str,
        genre: str,
        search_context: str,
    ) -> List[Dict[str, str]]:
        """Build detailed tagging request."""
        track_info = {
            "title": title,
            "artist": artist,
            "album": album,
            "genre": genre,
        }
        
        if search_context:
            track_info["web_search_results"] = search_context
        
        payload = {
            "task": "detailed_music_tagging",
            "track": track_info,
            "request": [
                "Based on song info and web search results, generate 5-10 high-quality tags",
                "Tags should cover: style/genre, mood/atmosphere, era, language, and artist characteristics",
                "Provide a short analysis explaining why these tags were chosen",
            ],
            "response_schema": {
                "tags": ["tag1", "tag2", "..."],
                "analysis": "explanation",
            },
        }
        
        system = (
            "You are a professional music classification expert. Based on track metadata and info from web searches, "
            "generate accurate and detailed tags for this song. "
            "Web search results help you understand artist style, album features, and song background. "
            "Output pure JSON only, no other content."
        )
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def parse_detailed_response(self, content: str) -> Dict[str, Any]:
        """Parse detailed tagging response."""
        raw = strip_code_fences(content).strip()
        
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning("Detailed tagging LLM returned non-JSON: %s", raw[:200])
            return {"tags": [], "analysis": f"Parsing failed: {e}"}
        
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        
        # Filter for valid tags
        valid_tags = []
        for tag in tags:
            if isinstance(tag, str):
                tag = tag.strip()
                if tag and len(tag) <= 50:
                    valid_tags.append(tag)
        
        return {
            "tags": valid_tags,
            "analysis": data.get("analysis", ""),
        }
