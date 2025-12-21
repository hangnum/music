"""
Web Search Service

Uses DuckDuckGo to provide free web search functionality, assisting LLM in tagging.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search Result"""
    title: str
    body: str
    url: str


class WebSearchService:
    """
    Web Search Service
    
    Uses the DuckDuckGo search engine to retrieve music-related information,
    enhancing the accuracy of LLM tagging.
    
    Usage Example:
        service = WebSearchService()
        context = service.get_music_context("Jay Chou", "Qi Li Xiang", "Common Jasmine Orange")
        # -> "Style: R&B/Pop | Features: Chinese elements | ..."
    """
    
    # High-quality music information sites
    TRUSTED_SITES = [
        "music.163.com",
        "baike.baidu.com", 
        "douban.com",
        "qq.com",
    ]
    
    # Keywords to filter out irrelevant content
    NOISE_PATTERNS = [
        r"Login|Register|Download|Install|Ads",
        r"404|Page not found|Access error",
        r"Click.*View|Experience.*Now",
    ]
    
    def __init__(self, timeout: float = None, config=None):
        """
        Initialize the search service.
        
        Args:
            timeout: Request timeout (seconds); if None, read from configuration.
            config: ConfigService instance (optional).
        """
        # Get timeout from config or parameter
        if timeout is not None:
            self._timeout = timeout
        else:
            # Attempt to read from config, else use default
            try:
                from services.config_service import ConfigService
                config_obj = config or ConfigService()
                self._timeout = config_obj.get("llm.web_search.timeout", 10.0)
            except ImportError:
                self._timeout = 10.0
        
        # Whether web search is enabled
        try:
            from services.config_service import ConfigService
            config_obj = config or ConfigService()
            self._enabled = config_obj.get("llm.web_search.enabled", True)
        except ImportError:
            self._enabled = True
        
        self._ddgs = None
        self._noise_re = re.compile("|".join(self.NOISE_PATTERNS), re.IGNORECASE)
        # Cache: Use OrderedDict to implement LRU cache
        self._cache = OrderedDict()
        # Thread lock to protect cache access
        self._cache_lock = threading.RLock()
        # Maximum cache size, from config or default
        try:
            from services.config_service import ConfigService
            config_obj = config or ConfigService()
            self._max_cache_size = config_obj.get("llm.web_search.max_cache_size", 100)
        except ImportError:
            self._max_cache_size = 100
    
    def _get_ddgs(self):
        """Lazy load DDGS client."""
        if self._ddgs is None:
            try:
                from ddgs import DDGS
                self._ddgs = DDGS(timeout=self._timeout)
            except ImportError:
                logger.warning("ddgs not installed, please run: pip install ddgs")
                return None
        return self._ddgs
    
    def _clean_text(self, text: str) -> str:
        """Clean text, removing noise content."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Check for noise
        if self._noise_re.search(text):
            return ""
        return text
    
    def _is_relevant(self, body: str, keywords: List[str]) -> bool:
        """Check if the result is relevant to the keywords."""
        if not body or not keywords:
            return True  # Do not filter if no keywords provided
        body_lower = body.lower()
        return any(kw.lower() in body_lower for kw in keywords if kw)
    
    def _deduplicate(self, texts: List[str]) -> List[str]:
        """Deduplicate while preserving order."""
        seen: Set[str] = set()
        result = []
        for t in texts:
            # Use first 50 characters as deduplication key
            key = t[:50].lower() if len(t) >= 50 else t.lower()
            if key not in seen:
                seen.add(key)
                result.append(t)
        return result
    
    def search_music_info(
        self,
        artist: str,
        title: str,
        max_results: int = 5,
    ) -> List[str]:
        """
        Search for song information (improved version).
        
        Uses a multi-query strategy, prioritizing results from high-quality sites.
        
        Args:
            artist: Artist name
            title: Song title
            max_results: Maximum number of results to return
            
        Returns:
            List of search result summaries (filtered and deduplicated).
        """
        if not artist and not title:
            return []
        
        all_results = []
        keywords = [k for k in [artist, title] if k]
        
        # Strategy 1: Exact search (with quotes)
        if artist and title:
            query = f'"{artist}" "{title}" music style'
            results = self._do_search(query, max_results=3)
            all_results.extend(results)
        
        # Strategy 2: Generic search
        if len(all_results) < max_results:
            query_parts = keywords + ["song", "style"]
            query = " ".join(query_parts)
            results = self._do_search(query, max_results=3)
            all_results.extend(results)
        
        # Filter and deduplicate
        filtered = [r for r in all_results if self._is_relevant(r, keywords)]
        return self._deduplicate(filtered)[:max_results]
    
    def search_artist_info(
        self,
        artist: str,
        max_results: int = 3,
    ) -> List[str]:
        """
        Search for artist information.
        
        Args:
            artist: Artist name
            max_results: Maximum number of results to return
            
        Returns:
            List of search result summaries.
        """
        if not artist:
            return []
        
        # Use more precise query
        query = f'"{artist}" singer music style masterpiece'
        results = self._do_search(query, max_results=max_results + 2)
        
        # Filter results containing the artist's name
        filtered = [r for r in results if artist.lower() in r.lower()]
        return filtered[:max_results] if filtered else results[:max_results]
    
    def search_album_info(
        self,
        artist: str,
        album: str,
        max_results: int = 3,
    ) -> List[str]:
        """
        Search for album information.
        
        Args:
            artist: Artist name
            album: Album name
            max_results: Maximum number of results to return
            
        Returns:
            List of search result summaries.
        """
        if not album:
            return []
        
        # Exact search for album
        if artist:
            query = f'"{artist}" "{album}" album style'
        else:
            query = f'"{album}" album music style'
        
        results = self._do_search(query, max_results=max_results + 2)
        
        # Filter results containing the album's name
        filtered = [r for r in results if album.lower() in r.lower()]
        return filtered[:max_results] if filtered else results[:max_results]
    
    def _manage_cache_size(self):
        """Manage cache size, cleaning up the oldest entries (LRU) if it exceeds the limit."""
        with self._cache_lock:
            while len(self._cache) > self._max_cache_size:
                # Remove the oldest entry (the first key in OrderedDict)
                self._cache.popitem(last=False)
            logger.debug("Cache cleaned: retaining %d entries", len(self._cache))
    
    def _do_search(
        self,
        query: str,
        max_results: int,
    ) -> List[str]:
        """
        Perform the search.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of result summaries.
        """
        # Check if the service is enabled
        if not self._enabled:
            logger.debug("Web search service disabled, skipping: %s", query)
            return []
        
        cache_key = (query, max_results)
        
        # Check cache (thread-safe, LRU update)
        with self._cache_lock:
            if cache_key in self._cache:
                logger.debug("Cache hit: %s", query)
                # Move key to end to represent most recent use
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]
        
        ddgs = self._get_ddgs()
        if ddgs is None:
            return []
        
        try:
            results = list(ddgs.text(
                query,
                max_results=max_results,
                region="cn-zh",
            ))
            
            summaries = []
            for r in results:
                body = self._clean_text(r.get("body", ""))
                if not body:
                    continue
                
                # Limit result length, ensuring truncation at sentence boundaries
                if len(body) > 150:
                    # Attempt to truncate at a period
                    cut_pos = body.rfind("。", 0, 150)
                    if cut_pos > 50:
                        body = body[:cut_pos + 1]
                    else:
                        body = body[:150] + "…"
                
                summaries.append(body)
            
            logger.debug("Search for '%s' returned %d valid results", query, len(summaries))
            
            # Cache successful results (thread-safe)
            with self._cache_lock:
                self._cache[cache_key] = summaries
                # Move new key to end
                self._cache.move_to_end(cache_key)
                self._manage_cache_size()
            
            return summaries
            
        except Exception as e:
            logger.warning("Search failed: %s", e)
            return []
    
    def get_music_context(
        self,
        artist: Optional[str],
        title: Optional[str],
        album: Optional[str],
        max_total_chars: int = 500,
    ) -> str:
        """
        Get comprehensive music context information (improved version).
        
        Generates structured context for easier LLM parsing.
        
        Args:
            artist: Artist name
            title: Song title
            album: Album name
            max_total_chars: Maximum total characters
            
        Returns:
            Structured context string.
        """
        context_parts = []
        chars_used = 0
        
        # 1. Prioritize song information search
        if title:
            song_info = self.search_music_info(artist or "", title, max_results=2)
            for info in song_info:
                if chars_used + len(info) < max_total_chars * 0.6:
                    context_parts.append(f"[Song] {info}")
                    chars_used += len(info)
        
        # 2. Supplement with artist information
        if artist and chars_used < max_total_chars * 0.8:
            artist_info = self.search_artist_info(artist, max_results=1)
            for info in artist_info:
                if chars_used + len(info) < max_total_chars * 0.9:
                    context_parts.append(f"[Artist] {info}")
                    chars_used += len(info)
        
        # 3. Supplement with album information (if space permits)
        if album and chars_used < max_total_chars * 0.9:
            album_info = self.search_album_info(artist or "", album, max_results=1)
            for info in album_info:
                if chars_used + len(info) < max_total_chars:
                    context_parts.append(f"[Album] {info}")
                    chars_used += len(info)
        
        if not context_parts:
            return ""
        
        # Separate by newlines for easier LLM parsing
        context = "\n".join(context_parts)
        
        # Final length control
        if len(context) > max_total_chars:
            context = context[:max_total_chars - 3] + "..."
        
        return context
