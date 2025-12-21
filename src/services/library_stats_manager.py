"""
Library Statistics Manager Module

Responsible for playback statistics, counting, and track removal in the media library.
"""

from typing import List, Optional
import logging

from core.database import DatabaseManager
from core.event_bus import EventBus, EventType
from models.track import Track

logger = logging.getLogger(__name__)


class LibraryStatsManager:
    """
    Library Statistics Manager
    
    Handles playback statistics, counting, and track removal.
    """
    
    def __init__(self, db: DatabaseManager, event_bus: EventBus):
        self._db = db
        self._event_bus = event_bus
    
    def get_recent_tracks(self, limit: int = 20) -> List[Track]:
        """Get recently played tracks."""
        rows = self._db.fetch_all(
            """SELECT * FROM tracks 
               WHERE last_played IS NOT NULL
               ORDER BY last_played DESC LIMIT ?""",
            (limit,)
        )
        return [Track.from_dict(row) for row in rows]
    
    def get_most_played_tracks(self, limit: int = 20) -> List[Track]:
        """Get most played tracks."""
        rows = self._db.fetch_all(
            """SELECT * FROM tracks 
               WHERE play_count > 0
               ORDER BY play_count DESC LIMIT ?""",
            (limit,)
        )
        return [Track.from_dict(row) for row in rows]
    
    def update_play_stats(self, track_id: str) -> None:
        """Update playback statistics."""
        from datetime import datetime
        
        self._db.execute(
            """UPDATE tracks SET 
               play_count = play_count + 1,
               last_played = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), track_id)
        )
        self._db.commit()
    
    def remove_track(self, track_id: str) -> bool:
        """Remove a track from the library."""
        # Note: A simple DELETE is used here; real-world scenarios might need more complex logic.
        try:
            cursor = self._db.execute(
                "DELETE FROM tracks WHERE id = ?",
                (track_id,)
            )
            deleted = cursor.rowcount > 0
            if deleted:
                self._event_bus.publish(EventType.TRACK_REMOVED, track_id)
            return deleted
        except Exception as e:
            logger.warning("Failed to delete track: %s - %s", track_id, e)
            return False
    
    def get_track_count(self) -> int:
        """Get total number of tracks."""
        result = self._db.fetch_one("SELECT COUNT(*) as count FROM tracks")
        return result["count"] if result else 0
    
    def get_artist_count(self) -> int:
        """Get total number of artists."""
        result = self._db.fetch_one("SELECT COUNT(*) as count FROM artists")
        return result["count"] if result else 0
    
    def get_album_count(self) -> int:
        """Get total number of albums."""
        result = self._db.fetch_one("SELECT COUNT(*) as count FROM albums")
        return result["count"] if result else 0
    
    def get_total_duration_ms(self) -> int:
        """Get total playback duration (milliseconds)."""
        result = self._db.fetch_one("SELECT COALESCE(SUM(duration_ms), 0) as total_ms FROM tracks")
        return result["total_ms"] if result else 0
    
    def get_total_play_count(self) -> int:
        """Get total number of playbacks."""
        result = self._db.fetch_one("SELECT COALESCE(SUM(play_count), 0) as total_plays FROM tracks")
        return result["total_plays"] if result else 0