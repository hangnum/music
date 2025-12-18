"""
标签模型测试
"""

import pytest



class TestTagModel:
    """Tag 模型测试"""
    
    def test_tag_creation(self):
        """测试创建标签"""
        from models.tag import Tag
        
        tag = Tag(name="喜欢", color="#FF5733")
        
        assert tag.name == "喜欢"
        assert tag.color == "#FF5733"
        assert tag.id is not None
        assert tag.created_at is not None
    
    def test_tag_default_color(self):
        """测试默认颜色"""
        from models.tag import Tag
        
        tag = Tag(name="测试")
        
        assert tag.color == "#808080"
    
    def test_tag_to_dict(self):
        """测试序列化为字典"""
        from models.tag import Tag
        
        tag = Tag(id="test-id", name="摇滚", color="#FF0000")
        data = tag.to_dict()
        
        assert data['id'] == "test-id"
        assert data['name'] == "摇滚"
        assert data['color'] == "#FF0000"
        assert 'created_at' in data
    
    def test_tag_from_dict(self):
        """测试从字典反序列化"""
        from models.tag import Tag
        
        data = {
            'id': 'tag-123',
            'name': '古典',
            'color': '#0000FF',
            'created_at': '2024-01-01T12:00:00'
        }
        
        tag = Tag.from_dict(data)
        
        assert tag.id == 'tag-123'
        assert tag.name == '古典'
        assert tag.color == '#0000FF'
    
    def test_tag_from_dict_missing_fields(self):
        """测试从不完整字典反序列化"""
        from models.tag import Tag
        
        data = {'name': '流行'}
        tag = Tag.from_dict(data)
        
        assert tag.name == '流行'
        assert tag.color == '#808080'  # 默认颜色
        assert tag.id is not None  # 自动生成 ID
    
    def test_tag_equality(self):
        """测试标签相等性"""
        from models.tag import Tag
        
        tag1 = Tag(id="same-id", name="标签1")
        tag2 = Tag(id="same-id", name="标签2")  # 相同 ID，不同名称
        tag3 = Tag(id="diff-id", name="标签1")  # 不同 ID，相同名称
        
        assert tag1 == tag2  # 基于 ID 相等
        assert tag1 != tag3  # ID 不同


class TestTrackWithTags:
    """Track 模型标签字段测试"""
    
    def test_track_default_tags(self):
        """测试曲目默认无标签"""
        from models.track import Track
        
        track = Track(title="测试歌曲")
        
        assert track.tags == []
    
    def test_track_with_tags(self):
        """测试创建带标签的曲目"""
        from models.track import Track
        
        track = Track(title="测试歌曲", tags=["摇滚", "经典"])
        
        assert len(track.tags) == 2
        assert "摇滚" in track.tags
        assert "经典" in track.tags
    
    def test_track_to_dict_with_tags(self):
        """测试带标签的曲目序列化"""
        from models.track import Track
        
        track = Track(title="测试歌曲", tags=["喜欢", "2024"])
        data = track.to_dict()
        
        assert 'tags' in data
        assert data['tags'] == ["喜欢", "2024"]
    
    def test_track_from_dict_with_tags(self):
        """测试从字典反序列化带标签的曲目"""
        from models.track import Track
        
        data = {
            'title': '测试歌曲',
            'tags': ['流行', '华语']
        }
        
        track = Track.from_dict(data)
        
        assert track.title == '测试歌曲'
        assert track.tags == ['流行', '华语']
    
    def test_track_from_dict_without_tags(self):
        """测试从无标签字典反序列化"""
        from models.track import Track
        
        data = {'title': '测试歌曲'}
        track = Track.from_dict(data)
        
        assert track.tags == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
