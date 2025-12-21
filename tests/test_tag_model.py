"""
Tag Model Tests
"""

import pytest



class TestTagModel:
    """Tests for the Tag model."""
    
    def test_tag_creation(self):
        """Test tag creation."""
        from models.tag import Tag
        
        tag = Tag(name="Favorite", color="#FF5733")
        
        assert tag.name == "Favorite"
        assert tag.color == "#FF5733"
        assert tag.id is not None
        assert tag.created_at is not None
    
    def test_tag_default_color(self):
        """Test default color."""
        from models.tag import Tag
        
        tag = Tag(name="Test")
        
        assert tag.color == "#808080"
    
    def test_tag_to_dict(self):
        """Test serialization to dictionary."""
        from models.tag import Tag
        
        tag = Tag(id="test-id", name="Rock", color="#FF0000")
        data = tag.to_dict()
        
        assert data['id'] == "test-id"
        assert data['name'] == "Rock"
        assert data['color'] == "#FF0000"
        assert 'created_at' in data
    
    def test_tag_from_dict(self):
        """Test deserialization from dictionary."""
        from models.tag import Tag
        
        data = {
            'id': 'tag-123',
            'name': 'Classical',
            'color': '#0000FF',
            'created_at': '2024-01-01T12:00:00'
        }
        
        tag = Tag.from_dict(data)
        
        assert tag.id == 'tag-123'
        assert tag.name == 'Classical'
        assert tag.color == '#0000FF'
    
    def test_tag_from_dict_missing_fields(self):
        """Test deserialization from incomplete dictionary."""
        from models.tag import Tag
        
        data = {'name': 'Pop'}
        tag = Tag.from_dict(data)
        
        assert tag.name == 'Pop'
        assert tag.color == '#808080'  # Default color
        assert tag.id is not None  # Auto-generated ID
    
    def test_tag_equality(self):
        """Test tag equality."""
        from models.tag import Tag
        
        tag1 = Tag(id="same-id", name="Tag 1")
        tag2 = Tag(id="same-id", name="Tag 2")  # Same ID, different name
        tag3 = Tag(id="diff-id", name="Tag 1")  # Different ID, same name
        
        assert tag1 == tag2  # Equality based on ID
        assert tag1 != tag3  # Different IDs



class TestTrackWithTags:
    """Tests for the tags field in the Track model."""
    
    def test_track_default_tags(self):
        """Test that tracks have no tags by default."""
        from models.track import Track
        
        track = Track(title="Test Song")
        
        assert track.tags == []
    
    def test_track_with_tags(self):
        """Test creating a track with tags."""
        from models.track import Track
        
        track = Track(title="Test Song", tags=["Rock", "Classic"])
        
        assert len(track.tags) == 2
        assert "Rock" in track.tags
        assert "Classic" in track.tags
    
    def test_track_to_dict_with_tags(self):
        """Test serialization of a track with tags."""
        from models.track import Track
        
        track = Track(title="Test Song", tags=["Favorite", "2024"])
        data = track.to_dict()
        
        assert 'tags' in data
        assert data['tags'] == ["Favorite", "2024"]
    
    def test_track_from_dict_with_tags(self):
        """Test deserialization of a track with tags from a dictionary."""
        from models.track import Track
        
        data = {
            'title': 'Test Song',
            'tags': ['Pop', 'Chinese']
        }
        
        track = Track.from_dict(data)
        
        assert track.title == 'Test Song'
        assert track.tags == ['Pop', 'Chinese']
    
    def test_track_from_dict_without_tags(self):
        """Test deserialization of a track without tags from a dictionary."""
        from models.track import Track
        
        data = {'title': 'Test Song'}
        track = Track.from_dict(data)
        
        assert track.tags == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
