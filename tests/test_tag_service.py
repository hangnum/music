"""
Tag Service Tests
"""

import pytest
import os



class TestTagService:
    """TagService Tests"""
    
    def setup_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        self.db = DatabaseManager("test_tag_service.db")
    
    def teardown_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        if os.path.exists("test_tag_service.db"):
            os.remove("test_tag_service.db")
    
    def test_create_tag(self):
        """Test tag creation."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        tag = service.create_tag("Favorite", "#FF5733")
        
        assert tag is not None
        assert tag.name == "Favorite"
        assert tag.color == "#FF5733"
    
    def test_create_duplicate_tag(self):
        """Test creating a duplicate tag (case-insensitive)."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        tag1 = service.create_tag("Rock")
        tag2 = service.create_tag("ROCK")  # Should return None
        tag3 = service.create_tag("rock")  # Should return None
        
        assert tag1 is not None
        assert tag2 is None
        assert tag3 is None
    
    def test_get_tag(self):
        """Test fetching a tag."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        created = service.create_tag("Test")
        
        fetched = service.get_tag(created.id)
        
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Test"
    
    def test_get_tag_by_name(self):
        """Test fetching a tag by name."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        service.create_tag("Classical")
        
        # Case-insensitive
        tag = service.get_tag_by_name("classical")
        assert tag is not None
        assert tag.name == "Classical"
    
    def test_get_all_tags(self):
        """Test fetching all tags."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        service.create_tag("Tag A")
        service.create_tag("Tag B")
        service.create_tag("Tag C")
        
        tags = service.get_all_tags()
        
        assert len(tags) == 3
    
    def test_update_tag(self):
        """Test updating a tag."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        tag = service.create_tag("Old Name", "#000000")
        
        result = service.update_tag(tag.id, name="New Name", color="#FFFFFF")
        
        assert result is True
        
        updated = service.get_tag(tag.id)
        assert updated.name == "New Name"
        assert updated.color == "#FFFFFF"
    
    def test_delete_tag(self):
        """Test deleting a tag."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        tag = service.create_tag("To Delete")
        
        result = service.delete_tag(tag.id)
        
        assert result is True
        assert service.get_tag(tag.id) is None
    
    def test_add_tag_to_track(self):
        """Test adding a tag to a track."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # Create a track first
        self.db.insert("tracks", {
            "id": "track-1",
            "title": "Test Song",
            "file_path": "test.mp3",
            "artist_name": "Test Artist",
            "album_name": "Test Album",
            "track_number": 1,
        })
        
        # Create a tag
        tag = service.create_tag("Favorite")
        
        # Add tag to track
        result = service.add_tag_to_track("track-1", tag.id)
        
        assert result is True
    
    def test_remove_tag_from_track(self):
        """Test removing a tag from a track."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # Create track and tag
        self.db.insert("tracks", {
            "id": "track-2",
            "title": "Test Song",
            "file_path": "test2.mp3",
            "artist_name": "A",
            "album_name": "B",
            "track_number": 1,
        })
        tag = service.create_tag("Temporary")
        service.add_tag_to_track("track-2", tag.id)
        
        # Remove tag
        result = service.remove_tag_from_track("track-2", tag.id)
        
        assert result is True
        assert len(service.get_track_tags("track-2")) == 0
    
    def test_get_track_tags(self):
        """Test fetching all tags for a track."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # Create track
        self.db.insert("tracks", {
            "id": "track-3",
            "title": "Test Song",
            "file_path": "test3.mp3",
            "artist_name": "A",
            "album_name": "B",
            "track_number": 1,
        })
        
        # Create multiple tags and add them
        tag1 = service.create_tag("Tag 1")
        tag2 = service.create_tag("Tag 2")
        service.add_tag_to_track("track-3", tag1.id)
        service.add_tag_to_track("track-3", tag2.id)
        
        tags = service.get_track_tags("track-3")
        
        assert len(tags) == 2
    
    def test_get_tracks_by_tag(self):
        """Test fetching all tracks associated with a specific tag."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # Create multiple tracks
        for i in range(3):
            self.db.insert("tracks", {
                "id": f"track-{i+10}",
                "title": f"Song {i+1}",
                "file_path": f"song{i+10}.mp3",
                "artist_name": "A",
                "album_name": "B",
                "track_number": i+1,
            })
        
        # Create tag and add to tracks
        tag = service.create_tag("Common Tag")
        service.add_tag_to_track("track-10", tag.id)
        service.add_tag_to_track("track-11", tag.id)
        
        track_ids = service.get_tracks_by_tag(tag.id)
        
        assert len(track_ids) == 2
        assert "track-10" in track_ids
        assert "track-11" in track_ids
    
    def test_set_track_tags(self):
        """Test bulk setting tags for a track."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # Create track
        self.db.insert("tracks", {
            "id": "track-20",
            "title": "Test Song",
            "file_path": "test20.mp3",
            "artist_name": "A",
            "album_name": "B",
            "track_number": 1,
        })
        
        # Create tags
        tag1 = service.create_tag("New Tag 1")
        tag2 = service.create_tag("New Tag 2")
        tag3 = service.create_tag("New Tag 3")
        
        # Add an initial tag
        service.add_tag_to_track("track-20", tag1.id)
        
        # Bulk set (should replace all existing)
        result = service.set_track_tags("track-20", [tag2.id, tag3.id])
        
        assert result is True
        
        tags = service.get_track_tags("track-20")
        tag_names = [t.name for t in tags]
        
        assert len(tags) == 2
        assert "New Tag 1" not in tag_names
        assert "New Tag 2" in tag_names
        assert "New Tag 3" in tag_names
    
    def test_search_tags(self):
        """Test searching for tags."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        service.create_tag("Rock Music")
        service.create_tag("Pop Music")
        service.create_tag("Classical")
        
        results = service.search_tags("Music")
        
        assert len(results) == 2
    
    def test_get_tag_count(self):
        """Test fetching the total number of tags."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        service.create_tag("Tag A")
        service.create_tag("Tag B")
        
        count = service.get_tag_count()
        
        assert count == 2
    
    def test_cascade_delete(self):
        """Test cascading deletion of associations when a tag is deleted."""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # Create track and tag
        self.db.insert("tracks", {
            "id": "track-30",
            "title": "Test Song",
            "file_path": "test30.mp3",
            "artist_name": "A",
            "album_name": "B",
            "track_number": 1,
        })
        
        tag = service.create_tag("To Be Deleted")
        service.add_tag_to_track("track-30", tag.id)
        
        # Delete tag
        service.delete_tag(tag.id)
        
        # Associations should also be removed
        tags = service.get_track_tags("track-30")
        assert len(tags) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
