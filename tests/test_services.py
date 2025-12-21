"""
Service Layer Tests
"""

import pytest
import os
import tempfile
import shutil


class TestConfigService:
    """Configuration Service Tests"""
    
    def setup_method(self):
        from services.config_service import ConfigService
        ConfigService.reset_instance()
        self._tmpdir = tempfile.mkdtemp(prefix="music-config-")
        self._config_path = os.path.join(self._tmpdir, "config.yaml")
    
    def teardown_method(self):
        from services.config_service import ConfigService
        ConfigService.reset_instance()
        shutil.rmtree(self._tmpdir, ignore_errors=True)
    
    def test_singleton(self):
        """Test singleton pattern."""
        from services.config_service import ConfigService
        
        config1 = ConfigService(self._config_path)
        config2 = ConfigService(self._config_path)
        assert config1 is config2
    
    def test_get_default(self):
        """Test getting default configuration."""
        from services.config_service import ConfigService
        
        config = ConfigService(self._config_path)
        
        # Test nested fetch (validates return type and range, independent of file content)
        volume = config.get("playback.default_volume", 0.5)
        assert isinstance(volume, (int, float))
        assert 0.0 <= volume <= 1.0
    
    def test_set_and_get(self):
        """Test set and get operations."""
        from services.config_service import ConfigService
        
        config = ConfigService(self._config_path)
        config.set("test.value", 123)
        
        assert config.get("test.value") == 123


class TestPlaylistService:
    """Playlist Service Tests"""
    
    def setup_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        self._tmpdir = tempfile.mkdtemp(prefix="music-playlist-db-")
        self._db_path = os.path.join(self._tmpdir, "test_playlist.db")
        self.db = DatabaseManager(self._db_path)
    
    def teardown_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        shutil.rmtree(self._tmpdir, ignore_errors=True)
    
    def test_create_playlist(self):
        """Test playlist creation."""
        from services.playlist_service import PlaylistService
        
        service = PlaylistService(self.db)
        playlist = service.create("Test Playlist", "This is a description")
        
        assert playlist.name == "Test Playlist"
        assert playlist.description == "This is a description"
    
    def test_get_playlist(self):
        """Test fetching a playlist."""
        from services.playlist_service import PlaylistService
        
        service = PlaylistService(self.db)
        created = service.create("Test Playlist")
        
        fetched = service.get(created.id)
        assert fetched is not None
        assert fetched.name == "Test Playlist"
    
    def test_delete_playlist(self):
        """Test playlist deletion."""
        from services.playlist_service import PlaylistService
        
        service = PlaylistService(self.db)
        playlist = service.create("To Delete")
        
        result = service.delete(playlist.id)
        assert result == True
        
        fetched = service.get(playlist.id)
        assert fetched is None


class TestLibraryService:
    """Library Service Tests"""
    
    def setup_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        self._tmpdir = tempfile.mkdtemp(prefix="music-library-db-")
        self._db_path = os.path.join(self._tmpdir, "test_library.db")
        self.db = DatabaseManager(self._db_path)
    
    def teardown_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        shutil.rmtree(self._tmpdir, ignore_errors=True)
    
    def test_get_all_tracks_empty(self):
        """Test fetching tracks from an empty library."""
        from services.library_service import LibraryService
        
        service = LibraryService(self.db)
        tracks = service.get_all_tracks()
        
        assert len(tracks) == 0
    
    def test_search_empty(self):
        """Test searching an empty library."""
        from services.library_service import LibraryService
        
        service = LibraryService(self.db)
        results = service.search("test")
        
        assert len(results["tracks"]) == 0
        assert len(results["albums"]) == 0
        assert len(results["artists"]) == 0
    
    def test_get_track_count(self):
        """Test track count retrieval."""
        from services.library_service import LibraryService
        
        service = LibraryService(self.db)
        count = service.get_track_count()
        
        assert count == 0

    def test_query_tracks_by_genre(self):
        """Test querying tracks by genre."""
        from services.library_service import LibraryService

        service = LibraryService(self.db)

        # Insert some tracks (no dependencies on scanning or metadata)
        self.db.insert(
            "tracks",
            {
                "id": "t1",
                "title": "Rock Song",
                "file_path": "rock1.mp3",
                "genre": "Rock",
                "artist_name": "A",
                "album_name": "X",
                "track_number": 1,
            },
        )
        self.db.insert(
            "tracks",
            {
                "id": "t2",
                "title": "Pop Song",
                "file_path": "pop1.mp3",
                "genre": "Pop",
                "artist_name": "B",
                "album_name": "Y",
                "track_number": 1,
            },
        )

        tracks = service.query_tracks(genre="Rock", limit=10, shuffle=False)
        assert [t.id for t in tracks] == ["t1"]


class TestPlayerService:
    """Player Service Tests"""
    
    def test_initial_state(self):
        """Test initial playback state."""
        from services.player_service import PlayerService, PlayMode
        from unittest.mock import MagicMock
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 1.0
        
        player = PlayerService(audio_engine=mock_engine)
        
        assert player.current_track is None
        assert len(player.queue) == 0
    
    def test_set_queue(self):
        """Test setting the playback queue."""
        from services.player_service import PlayerService
        from models.track import Track
        from unittest.mock import MagicMock
        
        mock_engine = MagicMock()
        player = PlayerService(audio_engine=mock_engine)
        
        tracks = [Track(title=f"Song {i}") for i in range(5)]
        player.set_queue(tracks)
        
        assert len(player.queue) == 5
    
    def test_play_mode_cycle(self):
        """Test play mode switching."""
        from services.player_service import PlayerService, PlayMode
        from unittest.mock import MagicMock
        
        mock_engine = MagicMock()
        player = PlayerService(audio_engine=mock_engine)
        
        initial_mode = player.get_play_mode()
        player.cycle_play_mode()
        
        assert player.get_play_mode() != initial_mode

    def test_track_started_published_synchronously(self):
        """TRACK_STARTED should fire before play() returns (to avoid cross-thread UI crashes)."""
        from services.player_service import PlayerService
        from core.event_bus import EventBus, EventType
        from core.audio_engine import PlayerState
        from models.track import Track
        from unittest.mock import MagicMock

        EventBus.reset_instance()
        try:
            mock_engine = MagicMock()
            mock_engine.load.return_value = True
            mock_engine.play.return_value = True
            mock_engine.get_position.return_value = 0
            mock_engine.get_duration.return_value = 0
            mock_engine.state = PlayerState.PLAYING
            mock_engine.volume = 1.0

            player = PlayerService(audio_engine=mock_engine)

            fired = {"value": False}

            def on_started(_track):
                fired["value"] = True

            EventBus().subscribe(EventType.TRACK_STARTED, on_started)

            track = Track(title="Song", file_path="song.mp3")
            assert player.play(track) is True
            assert fired["value"] is True
        finally:
            EventBus.reset_instance()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
