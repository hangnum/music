"""
Strict tests for Services, focusing on edge cases and complex logic.
"""

import os
import shutil
import tempfile
import pytest
from services.library_service import LibraryService
from services.config_service import ConfigService
from core.database import DatabaseManager
from core.event_bus import EventBus
from models.track import Track

class TestLibraryServiceStrict:
    
    @pytest.fixture
    def strict_env(self, tmp_path):
        """Setup a strict environment with temp DB and Config."""
        # Reset Singletons
        EventBus.reset_instance()
        DatabaseManager.reset_instance()
        
        # Setup Config
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            f.write("library_paths: []\n")
            
        config_service = ConfigService(str(config_path))
        
        # Setup DB
        db_path = tmp_path / "strict_library.db"
        db_manager = DatabaseManager(str(db_path))
        
        # Initialize tables (assuming LibraryService or someone does this usually, 
        # but for unit test we might need to ensure schema exists)
        # In this project, DatabaseManager usually handles schema init on creation or first access if implemented.
        # Let's assume schema init is automatic or done by LibraryService.
        
        service = LibraryService(db_manager)
        
        return service, tmp_path

    def test_scan_complex_structure(self, strict_env):
        """Test scanning a complex directory structure with mixed files."""
        service, root_dir = strict_env
        
        # Create structure:
        # /music
        #   /valid_album
        #     track1.mp3
        #     track2.flac
        #     cover.jpg (ignore)
        #   /empty_folder
        #   /corrupt_folder
        #     fake.mp3 (0 bytes)
        #     text.txt
        #   /deeply/nested/music
        #     track3.mp3
            
        music_dir = root_dir / "music"
        music_dir.mkdir()
        
        # 1. Valid Album
        (music_dir / "valid_album").mkdir()
        self._create_dummy_audio(music_dir / "valid_album" / "track1.mp3")
        self._create_dummy_audio(music_dir / "valid_album" / "track2.flac")
        (music_dir / "valid_album" / "cover.jpg").write_text("image data")
        
        # 2. Empty Folder
        (music_dir / "empty_folder").mkdir()
        
        # 3. Corrupt/Invalid
        (music_dir / "corrupt_folder").mkdir()
        (music_dir / "corrupt_folder" / "fake.mp3").write_text("") # Empty
        (music_dir / "corrupt_folder" / "text.txt").write_text("hello")
        
        # 4. Deeply Nested
        nested = music_dir / "deeply" / "nested" / "music"
        nested.mkdir(parents=True)
        self._create_dummy_audio(nested / "track3.mp3")
        
        # Mock metadata parser to avoid needing real audio files
        # We need to patch the MetadataParser used by LibraryService
        from unittest.mock import patch, MagicMock
        
        with patch('core.metadata.MetadataParser.parse') as mock_parse:
            # Setup mock return values
            def side_effect(path):
                path_str = str(path)
                m = MagicMock()
                m.year = 2020
                m.bitrate = 320
                m.sample_rate = 44100
                m.format = 'mp3'
                m.track_number = 1
                m.genre = 'Pop'
                m.duration_ms = 1000
                
                if path_str.endswith("track1.mp3"):
                    m.title = "Track 1"
                    m.artist = "Artist A"
                    m.album = "Album A"
                    return m
                if path_str.endswith("track2.flac"):
                    m.title = "Track 2"
                    m.artist = "Artist A"
                    m.album = "Album A"
                    return m
                if path_str.endswith("track3.mp3"):
                    m.title = "Track 3"
                    m.artist = "Artist B"
                    m.album = "Album B"
                    return m
                return None # Corrupt or non-audio
                
            mock_parse.side_effect = side_effect
            
            # Execute Scan
            service.scan([str(music_dir)])
            
            # Verify DB content
            tracks = service.get_all_tracks()
            assert len(tracks) == 3
            
            titles = sorted([t.title for t in tracks])
            assert titles == ["Track 1", "Track 2", "Track 3"]

    def _create_dummy_audio(self, path):
        """Create a file that looks like audio (exists)."""
        path.write_text("dummy audio content")

    def test_scan_resilience(self, strict_env):
        """Test that scanning doesn't crash on permission errors (simulated)."""
        service, root_dir = strict_env
        music_dir = root_dir / "protected_music"
        music_dir.mkdir()
        
        # Create a file
        self._create_dummy_audio(music_dir / "protected.mp3")
        
        # Mock os.walk to raise PermissionError on a specific subdirectory
        original_walk = os.walk
        
        def mock_walk(top, *args, **kwargs):
            if "protected_music" in str(top):
                # We yield the top once, but maybe error on sub?
                # Or checking the file raises error.
                # Let's verify `_add_track_from_file` resilience.
                yield (str(top), [], ["protected.mp3"])
            else:
                yield from original_walk(top, *args, **kwargs)
                
        # Patch the MetadataParser to raise OSError (simulating read permission denied)
        from unittest.mock import patch
        with patch('core.metadata.MetadataParser.parse', side_effect=OSError("Permission denied")):
            service.scan([str(music_dir)])
            
            # Should not crash, and DB should be empty
            tracks = service.get_all_tracks()
            assert len(tracks) == 0
