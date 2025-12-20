"""
FavoritesService 单元测试
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
    """FavoritesService 测试套件"""
    
    def setup_method(self):
        """测试前创建临时数据库"""
        DatabaseManager.reset_instance()
        self._tmpdir = tempfile.mkdtemp(prefix="music-favorites-db-")
        self._db_path = os.path.join(self._tmpdir, "test_favorites.db")
        self.db = DatabaseManager(self._db_path)
        self.playlist_service = PlaylistService(self.db)
        self.favorites = FavoritesService(self.db, self.playlist_service)
    
    def teardown_method(self):
        """测试后清理临时数据库"""
        DatabaseManager.reset_instance()
        shutil.rmtree(self._tmpdir, ignore_errors=True)
    
    def _make_track(self, track_id: str = "t1", title: str = "Test Song") -> Track:
        """创建测试用 Track 对象并插入数据库"""
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
        """测试首次调用时创建新收藏歌单"""
        playlist = self.favorites.get_or_create_playlist()
        
        assert playlist is not None
        assert playlist.name == FavoritesService.FAVORITES_NAME
        assert playlist.description == FavoritesService.FAVORITES_DESCRIPTION
    
    def test_get_or_create_playlist_returns_existing(self):
        """测试后续调用返回已存在的歌单"""
        playlist1 = self.favorites.get_or_create_playlist()
        playlist2 = self.favorites.get_or_create_playlist()
        
        assert playlist1.id == playlist2.id
    
    def test_get_playlist_id(self):
        """测试获取收藏歌单 ID"""
        playlist = self.favorites.get_or_create_playlist()
        playlist_id = self.favorites.get_playlist_id()
        
        assert playlist_id == playlist.id
    
    def test_add_track(self):
        """测试添加曲目到收藏"""
        track = self._make_track()
        
        result = self.favorites.add_track(track)
        
        assert result is True
        assert self.favorites.is_favorite(track.id)
    
    def test_remove_track(self):
        """测试从收藏移除曲目"""
        track = self._make_track()
        self.favorites.add_track(track)
        
        result = self.favorites.remove_track(track.id)
        
        assert result is True
        assert not self.favorites.is_favorite(track.id)
    
    def test_is_favorite_false_when_not_added(self):
        """测试未收藏时 is_favorite 返回 False"""
        track = self._make_track()
        
        assert not self.favorites.is_favorite(track.id)
    
    def test_get_favorite_ids_empty_initially(self):
        """测试初始状态收藏列表为空"""
        ids = self.favorites.get_favorite_ids()
        
        assert len(ids) == 0
    
    def test_get_favorite_ids_returns_added_tracks(self):
        """测试收藏后能正确获取曲目 ID"""
        track1 = self._make_track("t1", "Song 1")
        track2 = self._make_track("t2", "Song 2")
        
        self.favorites.add_track(track1)
        self.favorites.add_track(track2)
        
        ids = self.favorites.get_favorite_ids()
        
        assert len(ids) == 2
        assert "t1" in ids
        assert "t2" in ids
    
    def test_add_tracks_batch(self):
        """测试批量添加曲目"""
        tracks = [
            self._make_track(f"t{i}", f"Song {i}")
            for i in range(1, 4)
        ]
        
        count = self.favorites.add_tracks(tracks)
        
        assert count == 3
        assert len(self.favorites.get_favorite_ids()) == 3
    
    def test_remove_tracks_batch(self):
        """测试批量移除曲目"""
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
        """测试重复添加同一曲目返回 False"""
        track = self._make_track()
        
        result1 = self.favorites.add_track(track)
        result2 = self.favorites.add_track(track)
        
        assert result1 is True
        assert result2 is False  # 重复添加应失败
        assert len(self.favorites.get_favorite_ids()) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
