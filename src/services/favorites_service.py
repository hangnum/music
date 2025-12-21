"""Favorites Service

Provides favorites playlist management functionality, supports track favorite/unfavorite operations.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional, Set

from core.database import DatabaseManager
from models.playlist import Playlist
from models.track import Track
from services.playlist_service import PlaylistService

logger = logging.getLogger(__name__)


class FavoritesService:
    """Favorites Service"""

    FAVORITES_NAME = "My Favorites"
    FAVORITES_DESCRIPTION = "Favorite songs"
    FAVORITES_KEY = "favorites.playlist_id"

    def __init__(self, db: DatabaseManager, playlist_service: PlaylistService):
        self._db = db
        self._playlist_service = playlist_service

    def get_or_create_playlist(self) -> Playlist:
        """Get or create favorites playlist"""
        playlist_id = self._get_state_value(self.FAVORITES_KEY)
        if playlist_id:
            playlist = self._playlist_service.get(playlist_id)
            if playlist:
                return playlist

        playlist = self._playlist_service.create(
            self.FAVORITES_NAME,
            self.FAVORITES_DESCRIPTION,
        )
        self._set_state_value(self.FAVORITES_KEY, playlist.id)
        return playlist

    def get_playlist_id(self) -> str:
        """Get favorites playlist ID"""
        return self.get_or_create_playlist().id

    def get_favorite_ids(self) -> Set[str]:
        """Get all favorite track ID set"""
        playlist_id = self._get_state_value(self.FAVORITES_KEY)
        if playlist_id:
            playlist = self._playlist_service.get(playlist_id)
            if playlist:
                return set(playlist.track_ids)

        playlist = self.get_or_create_playlist()
        return set(playlist.track_ids)

    def is_favorite(self, track_id: str) -> bool:
        """Check if track is favorited"""
        return track_id in self.get_favorite_ids()

    def add_track(self, track: Track) -> bool:
        """Add track to favorites"""
        playlist = self.get_or_create_playlist()
        return self._playlist_service.add_track(playlist.id, track)

    def remove_track(self, track_id: str) -> bool:
        """Remove track from favorites"""
        playlist = self.get_or_create_playlist()
        return self._playlist_service.remove_track(playlist.id, track_id)

    def add_tracks(self, tracks: Iterable[Track]) -> int:
        """Add multiple tracks to favorites"""
        count = 0
        for track in tracks:
            if self.add_track(track):
                count += 1
        return count

    def remove_tracks(self, track_ids: Iterable[str]) -> int:
        """Remove multiple tracks from favorites"""
        count = 0
        for track_id in track_ids:
            if self.remove_track(track_id):
                count += 1
        return count

    def _get_state_value(self, key: str) -> Optional[str]:
        row = self._db.fetch_one("SELECT value FROM app_state WHERE key = ?", (key,))
        return row["value"] if row else None

    def _set_state_value(self, key: str, value: str) -> None:
        try:
            self._db.execute(
                "INSERT OR REPLACE INTO app_state(key, value, updated_at) VALUES(?, ?, CURRENT_TIMESTAMP)",
                (key, value),
            )
        except Exception:
            logger.warning("Failed to save state value: key=%s", key, exc_info=True)
