"""
Media Library Service Module

Manages scanning, indexing, and search functionality for the media library.

Refactored to Facade Pattern, coordinating the following sub-modules:
- LibraryScanner: File scanning and parsing
- LibraryIndexer: Artist/album caching and indexing
- LibraryQueryEngine: Query and search functionality
- LibraryStatsManager: Statistics and counting functionality
"""

from typing import Iterator, List, Optional, Callable, Dict, Any
import logging

from core.database import DatabaseManager
from core.event_bus import EventBus
from core.metadata import MetadataParser
from models.track import Track
from models.album import Album
from models.artist import Artist

from .library_scanner import LibraryScanner
from .library_indexer import LibraryIndexer
from .library_query_engine import LibraryQueryEngine
from .library_stats_manager import LibraryStatsManager

logger = logging.getLogger(__name__)


class LibraryService:
    """
    Media Library Service (Facade Pattern)
    
    Coordinates various sub-modules to provide a unified media library service interface.
    
    Example:
        library = LibraryService()
        
        # Scan directories
        library.scan(["D:/Music"])
        
        # Get all tracks
        tracks = library.get_all_tracks()
        
        # Search
        results = library.search("Jay Chou")
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        import warnings
        
        if db is None:
            # Deprecation warning: the pattern of creating dependencies internally will be removed.
            warnings.warn(
                "Creating DatabaseManager internally in LibraryService is deprecated. "
                "Use AppContainerFactory.create() to get a properly configured LibraryService instance. "
                "This fallback will be removed in a future version.",
                FutureWarning,
                stacklevel=2
            )
            db = DatabaseManager()
        
        self._db = db
        self._event_bus = EventBus()
        
        # Initialize sub-modules
        self._indexer = LibraryIndexer(self._db)
        self._scanner = LibraryScanner(self._db, self._event_bus, self._indexer)
        self._query_engine = LibraryQueryEngine(self._db)
        self._stats_manager = LibraryStatsManager(self._db, self._event_bus)
    
    # ===== Scanning Functionality =====
    
    def scan(self, directories: List[str], 
             progress_callback: Optional[Callable[[int, int, str], None]] = None) -> int:
        """Synchronously scan directories"""
        return self._scanner.scan(directories, progress_callback)
    
    def scan_async(self, directories: List[str]) -> None:
        """Asynchronously scan directories"""
        self._scanner.scan_async(directories)
    
    def stop_scan(self) -> None:
        """Stop scan"""
        self._scanner.stop_scan()
    
    def join_scan_thread(self, timeout: float = 5.0) -> None:
        """Wait for scan thread to finish"""
        self._scanner.join_scan_thread(timeout)
    
    def is_scanning(self) -> bool:
        """Check if scanning is in progress"""
        return self._scanner.is_scanning()
    

    
    # ===== Query Functionality =====
    
    def get_all_tracks(self) -> List[Track]:
        """Get all tracks"""
        return self._query_engine.get_all_tracks()
    
    def get_track(self, track_id: str) -> Optional[Track]:
        """Get single track"""
        return self._query_engine.get_track(track_id)
    
    def get_track_by_path(self, file_path: str) -> Optional[Track]:
        """Get track by file path"""
        return self._query_engine.get_track_by_path(file_path)
    
    def get_albums(self) -> List[Album]:
        """Get all albums"""
        return self._query_engine.get_albums()
    
    def get_album_tracks(self, album_id: str) -> List[Track]:
        """Get all tracks of an album"""
        return self._query_engine.get_album_tracks(album_id)
    
    def get_artists(self) -> List[Artist]:
        """Get all artists"""
        return self._query_engine.get_artists()
    
    def get_artist_tracks(self, artist_id: str) -> List[Track]:
        """Get all tracks of an artist"""
        return self._query_engine.get_artist_tracks(artist_id)
    
    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search media library"""
        return self._query_engine.search(query, limit)
    
    def query_tracks(
        self,
        query: str = "",
        genre: str = "",
        artist: str = "",
        album: str = "",
        limit: int = 50,
        shuffle: bool = True,
    ) -> List[Track]:
        """Select tracks from music library by conditions"""
        return self._query_engine.query_tracks(query, genre, artist, album, limit, shuffle)
    
    def get_top_genres(self, limit: int = 30) -> List[str]:
        """Get the list of most frequent genres"""
        return self._query_engine.get_top_genres(limit)
    
    def iter_tracks_brief(self, batch_size: int = 250, limit: Optional[int] = None) -> Iterator[List[Dict[str, Any]]]:
        """Iterate briefly through track information in music library with pagination"""
        return self._query_engine.iter_tracks_brief(batch_size, limit)
    
    def get_tracks_by_ids(self, track_ids: List[str]) -> List[Track]:
        """Batch get tracks by given ID list"""
        return self._query_engine.get_tracks_by_ids(track_ids)
    
    # ===== Statistics Functionality =====
    
    def get_recent_tracks(self, limit: int = 20) -> List[Track]:
        """Get recently played tracks"""
        return self._stats_manager.get_recent_tracks(limit)
    
    def get_most_played_tracks(self, limit: int = 20) -> List[Track]:
        """Get most played tracks"""
        return self._stats_manager.get_most_played_tracks(limit)
    
    def update_play_stats(self, track_id: str) -> None:
        """Update playback statistics"""
        self._stats_manager.update_play_stats(track_id)
    
    def remove_track(self, track_id: str) -> bool:
        """Remove track from library"""
        return self._stats_manager.remove_track(track_id)
    
    def get_track_count(self) -> int:
        """Get total track count"""
        return self._stats_manager.get_track_count()
    
    def get_artist_count(self) -> int:
        """Get total artist count"""
        return self._stats_manager.get_artist_count()
    
    def get_album_count(self) -> int:
        """Get total album count"""
        return self._stats_manager.get_album_count()
    
    def get_total_duration_ms(self) -> int:
        """Get total playback duration (ms)"""
        return self._stats_manager.get_total_duration_ms()
    
    def get_total_play_count(self) -> int:
        """Get total playback count"""
        return self._stats_manager.get_total_play_count()
    
    # ===== Cache Cleanup =====
    
    def clear_caches(self) -> None:
        """Clear caches"""
        self._indexer.clear_caches()
    
    # ===== Property Access =====
    
    @property
    def db(self) -> DatabaseManager:
        """Get database manager"""
        return self._db
    
    @property
    def event_bus(self) -> EventBus:
        """Get event bus"""
        return self._event_bus