"""
服务层测试
"""

import pytest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestConfigService:
    """配置服务测试"""
    
    def setup_method(self):
        from services.config_service import ConfigService
        ConfigService.reset_instance()
    
    def teardown_method(self):
        from services.config_service import ConfigService
        ConfigService.reset_instance()
    
    def test_singleton(self):
        """测试单例模式"""
        from services.config_service import ConfigService
        
        config1 = ConfigService()
        config2 = ConfigService()
        assert config1 is config2
    
    def test_get_default(self):
        """测试获取默认配置"""
        from services.config_service import ConfigService
        
        config = ConfigService()
        
        # 测试嵌套获取
        volume = config.get("playback.default_volume", 0.5)
        assert volume == 0.8 or volume == 0.5  # 取决于是否有配置文件
    
    def test_set_and_get(self):
        """测试设置和获取"""
        from services.config_service import ConfigService
        
        config = ConfigService()
        config.set("test.value", 123)
        
        assert config.get("test.value") == 123


class TestPlaylistService:
    """播放列表服务测试"""
    
    def setup_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        self.db = DatabaseManager("test_playlist.db")
    
    def teardown_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        if os.path.exists("test_playlist.db"):
            os.remove("test_playlist.db")
    
    def test_create_playlist(self):
        """测试创建播放列表"""
        from services.playlist_service import PlaylistService
        
        service = PlaylistService(self.db)
        playlist = service.create("测试列表", "这是描述")
        
        assert playlist.name == "测试列表"
        assert playlist.description == "这是描述"
    
    def test_get_playlist(self):
        """测试获取播放列表"""
        from services.playlist_service import PlaylistService
        
        service = PlaylistService(self.db)
        created = service.create("测试列表")
        
        fetched = service.get(created.id)
        assert fetched is not None
        assert fetched.name == "测试列表"
    
    def test_delete_playlist(self):
        """测试删除播放列表"""
        from services.playlist_service import PlaylistService
        
        service = PlaylistService(self.db)
        playlist = service.create("待删除")
        
        result = service.delete(playlist.id)
        assert result == True
        
        fetched = service.get(playlist.id)
        assert fetched is None


class TestLibraryService:
    """媒体库服务测试"""
    
    def setup_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        self.db = DatabaseManager("test_library.db")
    
    def teardown_method(self):
        from core.database import DatabaseManager
        DatabaseManager.reset_instance()
        if os.path.exists("test_library.db"):
            os.remove("test_library.db")
    
    def test_get_all_tracks_empty(self):
        """测试空库获取曲目"""
        from services.library_service import LibraryService
        
        service = LibraryService(self.db)
        tracks = service.get_all_tracks()
        
        assert len(tracks) == 0
    
    def test_search_empty(self):
        """测试空库搜索"""
        from services.library_service import LibraryService
        
        service = LibraryService(self.db)
        results = service.search("测试")
        
        assert len(results["tracks"]) == 0
        assert len(results["albums"]) == 0
        assert len(results["artists"]) == 0
    
    def test_get_track_count(self):
        """测试曲目计数"""
        from services.library_service import LibraryService
        
        service = LibraryService(self.db)
        count = service.get_track_count()
        
        assert count == 0


class TestPlayerService:
    """播放服务测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
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
        """测试设置队列"""
        from services.player_service import PlayerService
        from models.track import Track
        from unittest.mock import MagicMock
        
        mock_engine = MagicMock()
        player = PlayerService(audio_engine=mock_engine)
        
        tracks = [Track(title=f"Song {i}") for i in range(5)]
        player.set_queue(tracks)
        
        assert len(player.queue) == 5
    
    def test_play_mode_cycle(self):
        """测试播放模式切换"""
        from services.player_service import PlayerService, PlayMode
        from unittest.mock import MagicMock
        
        mock_engine = MagicMock()
        player = PlayerService(audio_engine=mock_engine)
        
        initial_mode = player.get_play_mode()
        player.cycle_play_mode()
        
        assert player.get_play_mode() != initial_mode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
