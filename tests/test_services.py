"""
服务层测试
"""

import pytest
import os
import tempfile
import shutil


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
        
        # 测试嵌套获取（只验证返回类型和有效范围，不依赖配置文件内容）
        volume = config.get("playback.default_volume", 0.5)
        assert isinstance(volume, (int, float))
        assert 0.0 <= volume <= 1.0
    
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

    def test_query_tracks_by_genre(self):
        from services.library_service import LibraryService

        service = LibraryService(self.db)

        # 插入一些曲目（不依赖扫描/元数据）
        self.db.insert(
            "tracks",
            {
                "id": "t1",
                "title": "Rock Song",
                "file_path": "rock1.mp3",
                "genre": "摇滚",
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
                "genre": "流行",
                "artist_name": "B",
                "album_name": "Y",
                "track_number": 1,
            },
        )

        tracks = service.query_tracks(genre="摇滚", limit=10, shuffle=False)
        assert [t.id for t in tracks] == ["t1"]


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

    def test_track_started_published_synchronously(self):
        """TRACK_STARTED 应在 play() 返回前触发（避免跨线程 UI 崩溃）"""
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
