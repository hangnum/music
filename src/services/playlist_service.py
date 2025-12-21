"""
Playlist Service Module

Manages CRUD operations for playlists.
"""

from typing import List, Optional
from datetime import datetime
import uuid
import logging

from core.database import DatabaseManager
from core.event_bus import EventBus, EventType
from models.playlist import Playlist
from models.track import Track

logger = logging.getLogger(__name__)


class PlaylistService:
    """
    Playlist Service
    
    Provides create, read, update, delete functions for playlists.
    
    Usage example:
        service = PlaylistService()
        
        # Create playlist
        playlist = service.create("My Favorites", "Favorite songs")
        
        # Add track
        service.add_track(playlist.id, track)
        
        # Get all playlists
        all_playlists = service.get_all()
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        self._db = db or DatabaseManager()
        self._event_bus = EventBus()
    
    def create(self, name: str, description: str = "") -> Playlist:
        """
        Create playlist
        
        Args:
            name: Playlist name
            description: Description
            
        Returns:
            Playlist: Created playlist
        """
        playlist_id = str(uuid.uuid4())
        now = datetime.now()
        
        self._db.insert("playlists", {
            "id": playlist_id,
            "name": name,
            "description": description,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        })
        
        playlist = Playlist(
            id=playlist_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        
        self._event_bus.publish(EventType.PLAYLIST_CREATED, playlist)
        return playlist
    
    def get(self, playlist_id: str) -> Optional[Playlist]:
        """
        Get playlist
        
        Args:
            playlist_id: Playlist ID
            
        Returns:
            Playlist: Playlist object, returns None if not exists
        """
        row = self._db.fetch_one(
            "SELECT * FROM playlists WHERE id = ?",
            (playlist_id,)
        )
        
        if not row:
            return None
        
        # Get track ID list
        tracks_rows = self._db.fetch_all(
            """SELECT track_id FROM playlist_tracks 
               WHERE playlist_id = ? ORDER BY position""",
            (playlist_id,)
        )
        track_ids = [r["track_id"] for r in tracks_rows]
        
        # Calculate statistics
        stats = self._db.fetch_one(
            """SELECT COUNT(*) as count, COALESCE(SUM(t.duration_ms), 0) as duration
               FROM playlist_tracks pt
               JOIN tracks t ON pt.track_id = t.id
               WHERE pt.playlist_id = ?""",
            (playlist_id,)
        )
        
        return Playlist(
            id=row["id"],
            name=row["name"],
            description=row.get("description", ""),
            cover_path=row.get("cover_path"),
            track_ids=track_ids,
            track_count=stats["count"] if stats else 0,
            total_duration_ms=stats["duration"] if stats else 0,
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
        )
    
    def get_all(self) -> List[Playlist]:
        """
        Get all playlists.
        
        Returns:
            List[Playlist]: List of playlists.
        """
        rows = self._db.fetch_all(
            "SELECT id FROM playlists ORDER BY created_at DESC"
        )
        
        return [self.get(row["id"]) for row in rows if self.get(row["id"])]
    
    def update(self, playlist_id: str, name: str = None, 
               description: str = None) -> bool:
        """
        Update a playlist.
        
        Args:
            playlist_id: Playlist ID
            name: New name
            description: New description
            
        Returns:
            bool: True if update was successful.
        """
        updates = {"updated_at": datetime.now().isoformat()}
        
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        
        rows_affected = self._db.update(
            "playlists",
            updates,
            "id = ?",
            (playlist_id,)
        )
        
        if rows_affected > 0:
            playlist = self.get(playlist_id)
            if playlist:
                self._event_bus.publish(EventType.PLAYLIST_UPDATED, playlist)
            return True
        return False
    
    def delete(self, playlist_id: str) -> bool:
        """
        Delete a playlist.
        
        Args:
            playlist_id: Playlist ID
            
        Returns:
            bool: True if deletion was successful.
        """
        rows_affected = self._db.delete("playlists", "id = ?", (playlist_id,))
        
        if rows_affected > 0:
            self._event_bus.publish(EventType.PLAYLIST_DELETED, playlist_id)
            return True
        return False
    
    def add_track(self, playlist_id: str, track: Track) -> bool:
        """
        Add a track to a playlist.
        
        Args:
            playlist_id: Playlist ID
            track: Track object
            
        Returns:
            bool: True if successfully added.
        """
        # Get current maximum position
        result = self._db.fetch_one(
            "SELECT MAX(position) as max_pos FROM playlist_tracks WHERE playlist_id = ?",
            (playlist_id,)
        )
        next_pos = (result["max_pos"] or 0) + 1 if result else 1
        
        try:
            self._db.insert("playlist_tracks", {
                "playlist_id": playlist_id,
                "track_id": track.id,
                "position": next_pos,
                "added_at": datetime.now().isoformat(),
            })
            
            # Update the playlist's update time
            self._db.update(
                "playlists",
                {"updated_at": datetime.now().isoformat()},
                "id = ?",
                (playlist_id,)
            )
            
            self._event_bus.publish(EventType.PLAYLIST_UPDATED, self.get(playlist_id))
            return True
        except Exception as e:
            logger.warning("Failed to add track to playlist: playlist_id=%s, track_id=%s, error=%s", playlist_id, track.id, e)
            return False
    
    def remove_track(self, playlist_id: str, track_id: str) -> bool:
        """
        Remove a track from a playlist.
        
        Args:
            playlist_id: Playlist ID
            track_id: Track ID
            
        Returns:
            bool: True if successfully removed.
        """
        rows_affected = self._db.delete(
            "playlist_tracks",
            "playlist_id = ? AND track_id = ?",
            (playlist_id, track_id)
        )
        
        if rows_affected > 0:
            # Update the playlist's update time
            self._db.update(
                "playlists",
                {"updated_at": datetime.now().isoformat()},
                "id = ?",
                (playlist_id,)
            )
            
            self._event_bus.publish(EventType.PLAYLIST_UPDATED, self.get(playlist_id))
            return True
        return False
    
    def reorder_track(self, playlist_id: str, track_id: str, 
                      new_position: int) -> bool:
        """
        Adjust the order of a track in a playlist.
        
        Args:
            playlist_id: Playlist ID
            track_id: Track ID
            new_position: New position
            
        Returns:
            bool: True if successfully reordered.
        """
        # Get current position
        current = self._db.fetch_one(
            "SELECT position FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
            (playlist_id, track_id)
        )
        
        if not current:
            return False
        
        old_position = current["position"]
        
        if old_position == new_position:
            return True
        
        with self._db.transaction():
            if old_position < new_position:
                # Move backwards: positions in between decrease by 1
                self._db.execute(
                    """UPDATE playlist_tracks SET position = position - 1
                       WHERE playlist_id = ? AND position > ? AND position <= ?""",
                    (playlist_id, old_position, new_position)
                )
            else:
                # Move forwards: positions in between increase by 1
                self._db.execute(
                    """UPDATE playlist_tracks SET position = position + 1
                       WHERE playlist_id = ? AND position >= ? AND position < ?""",
                    (playlist_id, new_position, old_position)
                )
            
            # Update target track position
            self._db.execute(
                "UPDATE playlist_tracks SET position = ? WHERE playlist_id = ? AND track_id = ?",
                (new_position, playlist_id, track_id)
            )
        
        self._event_bus.publish(EventType.PLAYLIST_UPDATED, self.get(playlist_id))
        return True
    
    def get_tracks(self, playlist_id: str) -> List[Track]:
        """
        Get all tracks in a playlist.
        
        Args:
            playlist_id: Playlist ID
            
        Returns:
            List[Track]: List of tracks.
        """
        rows = self._db.fetch_all(
            """SELECT t.* FROM tracks t
               JOIN playlist_tracks pt ON t.id = pt.track_id
               WHERE pt.playlist_id = ?
               ORDER BY pt.position""",
            (playlist_id,)
        )
        
        return [Track.from_dict(row) for row in rows]
