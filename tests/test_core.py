"""
Core Module Tests
"""

import pytest
import os



class TestEventBus:
    """Event Bus Tests"""
    
    def setup_method(self):
        """Reset singleton before each test."""
        from core.event_bus import EventBus
        EventBus.reset_instance()
    
    def teardown_method(self):
        """Clean up after each test."""
        from core.event_bus import EventBus
        EventBus.reset_instance()
    
    def test_singleton(self):
        """Test singleton pattern."""
        from core.event_bus import EventBus
        
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2
    
    def test_subscribe_and_publish(self):
        """Test subscription and publication."""
        from core.event_bus import EventBus, EventType
        
        bus = EventBus()
        received_data = []
        
        def callback(data):
            received_data.append(data)
        
        bus.subscribe(EventType.TRACK_STARTED, callback)
        bus.publish_sync(EventType.TRACK_STARTED, {"title": "Test Song"})
        
        assert len(received_data) == 1
        assert received_data[0]["title"] == "Test Song"
    
    def test_unsubscribe(self):
        """Test unsubscription."""
        from core.event_bus import EventBus, EventType
        
        bus = EventBus()
        received_data = []
        
        def callback(data):
            received_data.append(data)
        
        sub_id = bus.subscribe(EventType.TRACK_STARTED, callback)
        bus.unsubscribe(sub_id)
        bus.publish_sync(EventType.TRACK_STARTED, {"title": "Test"})
        
        assert len(received_data) == 0


class TestMetadataParser:
    """Metadata Parser Tests"""
    
    def test_supported_formats(self):
        """Test supported formats."""
        from core.metadata import MetadataParser
        
        formats = MetadataParser.get_supported_formats()
        assert '.mp3' in formats
        assert '.flac' in formats
        assert '.wav' in formats
    
    def test_is_supported(self):
        """Test format checking."""
        from core.metadata import MetadataParser
        
        assert MetadataParser.is_supported("test.mp3") == True
        assert MetadataParser.is_supported("test.flac") == True
        assert MetadataParser.is_supported("test.txt") == False
    
    def test_parse_nonexistent_file(self):
        """Test parsing a non-existent file."""
        from core.metadata import MetadataParser
        
        result = MetadataParser.parse("nonexistent.mp3")
        assert result is None


class TestDatabaseManager:
    """Database Manager Tests"""
    
    def setup_method(self):
        """Reset before each test."""
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
    
    def teardown_method(self):
        """Clean up after each test."""
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        # Delete test database
        if os.path.exists("test_music.db"):
            os.remove("test_music.db")
    
    def test_singleton(self):
        """Test singleton pattern."""
        from core.database import DatabaseManager
        
        db1 = DatabaseManager("test_music.db")
        db2 = DatabaseManager()
        assert db1 is db2
    
    def test_insert_and_fetch(self):
        """Test insert and query."""
        from core.database import DatabaseManager
        import uuid
        
        db = DatabaseManager("test_music.db")
        
        # Insert artist
        artist_id = str(uuid.uuid4())
        db.insert("artists", {
            "id": artist_id,
            "name": "Test Artist"
        })
        
        # Query
        result = db.fetch_one(
            "SELECT * FROM artists WHERE id = ?", 
            (artist_id,)
        )
        
        assert result is not None
        assert result["name"] == "Test Artist"
    
    def test_update(self):
        """Test update."""
        from core.database import DatabaseManager
        import uuid
        
        db = DatabaseManager("test_music.db")
        
        artist_id = str(uuid.uuid4())
        db.insert("artists", {"id": artist_id, "name": "Old Name"})
        
        db.update("artists", {"name": "New Name"}, "id = ?", (artist_id,))
        
        result = db.fetch_one("SELECT * FROM artists WHERE id = ?", (artist_id,))
        assert result["name"] == "New Name"
    
    def test_delete(self):
        """Test deletion."""
        from core.database import DatabaseManager
        import uuid
        
        db = DatabaseManager("test_music.db")
        
        artist_id = str(uuid.uuid4())
        db.insert("artists", {"id": artist_id, "name": "To Delete"})
        
        db.delete("artists", "id = ?", (artist_id,))
        
        result = db.fetch_one("SELECT * FROM artists WHERE id = ?", (artist_id,))
        assert result is None


class TestTrackModel:
    """Track Model Tests"""
    
    def test_duration_str(self):
        """Test duration formatting."""
        from models.track import Track
        
        track = Track(duration_ms=185000)  # 3:05
        assert track.duration_str == "3:05"
    
    def test_display_name(self):
        """Test display name."""
        from models.track import Track
        
        track1 = Track(title="Song", artist_name="Artist")
        assert track1.display_name == "Artist - Song"
        
        track2 = Track(title="Song")
        assert track2.display_name == "Song"
    
    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        from models.track import Track
        
        track = Track(
            title="Test Song",
            artist_name="Test Artist",
            duration_ms=180000
        )
        
        data = track.to_dict()
        restored = Track.from_dict(data)
        
        assert restored.title == track.title
        assert restored.artist_name == track.artist_name
        assert restored.duration_ms == track.duration_ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
