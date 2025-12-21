"""
Library Indexer Module

Responsible for artist and album cache management and metadata indexing functions.
"""

from typing import Dict, Optional, Tuple
import uuid
import threading
import logging

from core.database import DatabaseManager
from core.metadata import AudioMetadata
from models.track import Track

logger = logging.getLogger(__name__)


class LibraryIndexer:
    """
    Library Indexer
    
    Handles caching, creation, and indexing logic for artists and albums.
    """
    
    def __init__(self, db: DatabaseManager):
        self._db = db
        self._lock = threading.RLock()
        # Cache during scanning (reduces repeated queries)
        self._artist_cache: Dict[str, str] = {}
        self._album_cache: Dict[Tuple[str, Optional[str]], str] = {}
    
    def get_or_create_artist(self, name: str, commit: bool = True) -> str:
        """Get or create an artist (using cache)."""
        # Check cache first
        with self._lock:
            if name in self._artist_cache:
                return self._artist_cache[name]
        
        existing = self._db.fetch_one(
            "SELECT id FROM artists WHERE name = ?",
            (name,)
        )
        
        if existing:
            with self._lock:
                self._artist_cache[name] = existing["id"]
            return existing["id"]
        
        artist_id = str(uuid.uuid4())
        self._db.execute(
            "INSERT INTO artists (id, name, created_at) VALUES (?, ?, ?)",
            (artist_id, name, self._get_current_timestamp())
        )
        if commit:
            self._db.commit()
        
        with self._lock:
            self._artist_cache[name] = artist_id
        return artist_id
    
    def get_or_create_album(self, title: str, artist_id: Optional[str],
                           year: Optional[int], commit: bool = True) -> str:
        """Get or create an album (using cache)."""
        # Cache key: (title, artist_id)
        cache_key = (title, artist_id)
        with self._lock:
            if cache_key in self._album_cache:
                return self._album_cache[cache_key]
        
        if artist_id:
            existing = self._db.fetch_one(
                "SELECT id FROM albums WHERE title = ? AND artist_id = ?",
                (title, artist_id)
            )
        else:
            existing = self._db.fetch_one(
                "SELECT id FROM albums WHERE title = ? AND artist_id IS NULL",
                (title,)
            )
        
        if existing:
            with self._lock:
                self._album_cache[cache_key] = existing["id"]
            return existing["id"]
        
        album_id = str(uuid.uuid4())
        self._db.execute(
            "INSERT INTO albums (id, title, artist_id, year, created_at) VALUES (?, ?, ?, ?, ?)",
            (album_id, title, artist_id, year, self._get_current_timestamp())
        )
        if commit:
            self._db.commit()
        
        with self._lock:
            self._album_cache[cache_key] = album_id
        return album_id
    
    def create_track_from_metadata(self, metadata: AudioMetadata, file_path: str,
                                  artist_id: Optional[str] = None, 
                                  album_id: Optional[str] = None,
                                  commit: bool = True) -> Optional[Track]:
        """
        Create a track from metadata.
        
        Args:
            metadata: Audio metadata
            file_path: Audio file path
            artist_id: Artist ID (optional)
            album_id: Album ID (optional)
            commit: Whether to commit immediately
            
        Returns:
            Optional[Track]: Created track object
        """
        from datetime import datetime
        
        track_id = str(uuid.uuid4())
        track_data = {
            "id": track_id,
            "title": metadata.title,
            "file_path": file_path,
            "duration_ms": metadata.duration_ms,
            "bitrate": metadata.bitrate,
            "sample_rate": metadata.sample_rate,
            "format": metadata.format,
            "artist_id": artist_id,
            "artist_name": metadata.artist,
            "album_id": album_id,
            "album_name": metadata.album,
            "track_number": metadata.track_number,
            "genre": metadata.genre,
            "year": metadata.year,
            "created_at": datetime.now().isoformat(),
        }
        
        try:
            self._db.execute(
                """INSERT INTO tracks (id, title, file_path, duration_ms, bitrate, 
                   sample_rate, format, artist_id, artist_name, album_id, album_name, 
                   track_number, genre, year, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(track_data.values())
            )
            if commit:
                self._db.commit()
            return Track.from_dict(track_data)
        except Exception as e:
            logger.warning("Failed to create track: %s - %s", file_path, e)
            return None
    
    def clear_caches(self) -> None:
        """Clear caches."""
        with self._lock:
            self._artist_cache.clear()
            self._album_cache.clear()
    
    def _get_current_timestamp(self) -> str:
        """Get the current timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat()