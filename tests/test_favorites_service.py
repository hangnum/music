"""
FavoritesService Unit Tests
"""

import pytest
import os
import tempfile
import shutil

from core.database import DatabaseManager
from services.playlist_service import PlaylistService
from services.favorites_service import FavoritesService
from models.track import Track


class TestFavoritesService:
    """FavoritesService test suite."""
    
    def setup_method(self):
        """Create a temporary database before each test."""
        DatabaseManager.reset_instance()
        self._tmpdir = tempfile.mkdtemp(prefix="music-favorites-db-")
        self._db_path = os.path.join(self._tmpdir, "test_favorites.db")
        self.db = DatabaseManager(self._db_path)
        self.playlist_service = PlaylistService(self.db)
        self.favorites = FavoritesService(self.db, self.playlist_service)
    
    def teardown_method(self):
        """Clean up the temporary database after each test."""
        DatabaseManager.reset_instance()
        shutil.rmtree(self._tmpdir, ignore_errors=True)
    
    def _make_track(self, track_id: str = "t1", title: str = "Test Song") -> Track:
        """Create a Track object for testing and insert it into the database."""
        self.db.insert("tracks", {
            "id": track_id,
            "title": title,
            "file_path": f"/path/to/{track_id}.mp3",
            "artist_name": "Test Artist",
            "album_name": "Test Album",
            "track_number": 1,
        })
        return Track(id=track_id, title=title, file_path=f"/path/to/{track_id}.mp3")
    
    def test_get_or_create_playlist_creates_new(self):
        """Test creating a new favorites playlist on first call."""
        playlist = self.favorites.get_or_create_playlist()
        
        assert playlist is not None
        assert playlist.name == FavoritesService.FAVORITES_NAME
        assert playlist.description == FavoritesService.FAVORITES_DESCRIPTION
    
    def test_get_or_create_playlist_returns_existing(self):
        """Test returning the existing playlist on subsequent calls."""
        playlist1 = self.favorites.get_or_create_playlist()
        playlist2 = self.favorites.get_or_create_playlist()
        
        assert playlist1.id == playlist2.id
    
    def test_get_playlist_id(self):
        """Test getting the favorites playlist ID."""
        playlist = self.favorites.get_or_create_playlist()
        playlist_id = self.favorites.get_playlist_id()
        
        assert playlist_id == playlist.id
    
    def test_add_track(self):
        """Test adding a track to favorites."""
        track = self._make_track()
        
        result = self.favorites.add_track(track)
        
        assert result is True
        assert self.favorites.is_favorite(track.id)
    
    def test_remove_track(self):
        """Test removing a track from favorites."""
        track = self._make_track()
        self.favorites.add_track(track)
        
        result = self.favorites.remove_track(track.id)
        
        assert result is True
        assert not self.favorites.is_favorite(track.id)
    
    def test_is_favorite_false_when_not_added(self):
        """Test that is_favorite returns False when a track is not in favorites."""
        track = self._make_track()
        
        assert not self.favorites.is_favorite(track.id)
    
    def test_get_favorite_ids_empty_initially(self):
        """Test that the favorites list is initially empty."""
        ids = self.favorites.get_favorite_ids()
        
        assert len(ids) == 0
    
    def test_get_favorite_ids_returns_added_tracks(self):
        """Test that track IDs are correctly retrieved after being added to favorites."""
        track1 = self._make_track("t1", "Song 1")
        track2 = self._make_track("t2", "Song 2")
        
        self.favorites.add_track(track1)
        self.favorites.add_track(track2)
        
        ids = self.favorites.get_favorite_ids()
        
        assert len(ids) == 2
        assert "t1" in ids
        assert "t2" in ids
    
    def test_add_tracks_batch(self):
        """Test adding multiple tracks to favorites."""
        tracks = [
            self._make_track(f"t{i}", f"Song {i}")
            for i in range(1, 4)
        ]
        
        count = self.favorites.add_tracks(tracks)
        
        assert count == 3
        assert len(self.favorites.get_favorite_ids()) == 3
    
    def test_remove_tracks_batch(self):
        """Test removing multiple tracks from favorites."""
        tracks = [
            self._make_track(f"t{i}", f"Song {i}")
            for i in range(1, 4)
        ]
        self.favorites.add_tracks(tracks)
        
        count = self.favorites.remove_tracks(["t1", "t2"])
        
        assert count == 2
        ids = self.favorites.get_favorite_ids()
        assert len(ids) == 1
        assert "t3" in ids
    
    def test_add_same_track_twice_fails(self):
        """Test that adding the same track twice returns False."""
        track = self._make_track()
        
        result1 = self.favorites.add_track(track)
        result2 = self.favorites.add_track(track)
        
        assert result1 is True
        assert result2 is False  # Duplicate addition should fail
        assert len(self.favorites.get_favorite_ids()) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
