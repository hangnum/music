"""
核心模块测试
"""

import pytest
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestEventBus:
    """事件总线测试"""
    
    def setup_method(self):
        """每个测试前重置单例"""
        from core.event_bus import EventBus
        EventBus.reset_instance()
    
    def teardown_method(self):
        """每个测试后清理"""
        from core.event_bus import EventBus
        EventBus.reset_instance()
    
    def test_singleton(self):
        """测试单例模式"""
        from core.event_bus import EventBus
        
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2
    
    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
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
        """测试取消订阅"""
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
    """元数据解析器测试"""
    
    def test_supported_formats(self):
        """测试支持的格式"""
        from core.metadata import MetadataParser
        
        formats = MetadataParser.get_supported_formats()
        assert '.mp3' in formats
        assert '.flac' in formats
        assert '.wav' in formats
    
    def test_is_supported(self):
        """测试格式检查"""
        from core.metadata import MetadataParser
        
        assert MetadataParser.is_supported("test.mp3") == True
        assert MetadataParser.is_supported("test.flac") == True
        assert MetadataParser.is_supported("test.txt") == False
    
    def test_parse_nonexistent_file(self):
        """测试解析不存在的文件"""
        from core.metadata import MetadataParser
        
        result = MetadataParser.parse("nonexistent.mp3")
        assert result is None


class TestDatabaseManager:
    """数据库管理器测试"""
    
    def setup_method(self):
        """每个测试前重置"""
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
    
    def teardown_method(self):
        """每个测试后清理"""
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        # 删除测试数据库
        if os.path.exists("test_music.db"):
            os.remove("test_music.db")
    
    def test_singleton(self):
        """测试单例模式"""
        from core.database import DatabaseManager
        
        db1 = DatabaseManager("test_music.db")
        db2 = DatabaseManager()
        assert db1 is db2
    
    def test_insert_and_fetch(self):
        """测试插入和查询"""
        from core.database import DatabaseManager
        import uuid
        
        db = DatabaseManager("test_music.db")
        
        # 插入艺术家
        artist_id = str(uuid.uuid4())
        db.insert("artists", {
            "id": artist_id,
            "name": "Test Artist"
        })
        
        # 查询
        result = db.fetch_one(
            "SELECT * FROM artists WHERE id = ?", 
            (artist_id,)
        )
        
        assert result is not None
        assert result["name"] == "Test Artist"
    
    def test_update(self):
        """测试更新"""
        from core.database import DatabaseManager
        import uuid
        
        db = DatabaseManager("test_music.db")
        
        artist_id = str(uuid.uuid4())
        db.insert("artists", {"id": artist_id, "name": "Old Name"})
        
        db.update("artists", {"name": "New Name"}, "id = ?", (artist_id,))
        
        result = db.fetch_one("SELECT * FROM artists WHERE id = ?", (artist_id,))
        assert result["name"] == "New Name"
    
    def test_delete(self):
        """测试删除"""
        from core.database import DatabaseManager
        import uuid
        
        db = DatabaseManager("test_music.db")
        
        artist_id = str(uuid.uuid4())
        db.insert("artists", {"id": artist_id, "name": "To Delete"})
        
        db.delete("artists", "id = ?", (artist_id,))
        
        result = db.fetch_one("SELECT * FROM artists WHERE id = ?", (artist_id,))
        assert result is None


class TestTrackModel:
    """Track模型测试"""
    
    def test_duration_str(self):
        """测试时长格式化"""
        from models.track import Track
        
        track = Track(duration_ms=185000)  # 3:05
        assert track.duration_str == "3:05"
    
    def test_display_name(self):
        """测试显示名称"""
        from models.track import Track
        
        track1 = Track(title="Song", artist_name="Artist")
        assert track1.display_name == "Artist - Song"
        
        track2 = Track(title="Song")
        assert track2.display_name == "Song"
    
    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
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
