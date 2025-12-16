"""
标签服务测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestTagService:
    """TagService 测试"""
    
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
        """测试创建标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        tag = service.create_tag("喜欢", "#FF5733")
        
        assert tag is not None
        assert tag.name == "喜欢"
        assert tag.color == "#FF5733"
    
    def test_create_duplicate_tag(self):
        """测试创建重复标签（不区分大小写）"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        tag1 = service.create_tag("Rock")
        tag2 = service.create_tag("ROCK")  # 应该返回 None
        tag3 = service.create_tag("rock")  # 应该返回 None
        
        assert tag1 is not None
        assert tag2 is None
        assert tag3 is None
    
    def test_get_tag(self):
        """测试获取标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        created = service.create_tag("测试")
        
        fetched = service.get_tag(created.id)
        
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "测试"
    
    def test_get_tag_by_name(self):
        """测试按名称获取标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        service.create_tag("Classical")
        
        # 不区分大小写
        tag = service.get_tag_by_name("classical")
        assert tag is not None
        assert tag.name == "Classical"
    
    def test_get_all_tags(self):
        """测试获取所有标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        service.create_tag("A标签")
        service.create_tag("B标签")
        service.create_tag("C标签")
        
        tags = service.get_all_tags()
        
        assert len(tags) == 3
    
    def test_update_tag(self):
        """测试更新标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        tag = service.create_tag("旧名称", "#000000")
        
        result = service.update_tag(tag.id, name="新名称", color="#FFFFFF")
        
        assert result is True
        
        updated = service.get_tag(tag.id)
        assert updated.name == "新名称"
        assert updated.color == "#FFFFFF"
    
    def test_delete_tag(self):
        """测试删除标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        tag = service.create_tag("待删除")
        
        result = service.delete_tag(tag.id)
        
        assert result is True
        assert service.get_tag(tag.id) is None
    
    def test_add_tag_to_track(self):
        """测试为曲目添加标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # 先创建一个曲目
        self.db.insert("tracks", {
            "id": "track-1",
            "title": "测试歌曲",
            "file_path": "test.mp3",
            "artist_name": "测试艺术家",
            "album_name": "测试专辑",
            "track_number": 1,
        })
        
        # 创建标签
        tag = service.create_tag("喜欢")
        
        # 添加标签到曲目
        result = service.add_tag_to_track("track-1", tag.id)
        
        assert result is True
    
    def test_remove_tag_from_track(self):
        """测试移除曲目标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # 创建曲目和标签
        self.db.insert("tracks", {
            "id": "track-2",
            "title": "测试歌曲",
            "file_path": "test2.mp3",
            "artist_name": "A",
            "album_name": "B",
            "track_number": 1,
        })
        tag = service.create_tag("临时")
        service.add_tag_to_track("track-2", tag.id)
        
        # 移除标签
        result = service.remove_tag_from_track("track-2", tag.id)
        
        assert result is True
        assert len(service.get_track_tags("track-2")) == 0
    
    def test_get_track_tags(self):
        """测试获取曲目的所有标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # 创建曲目
        self.db.insert("tracks", {
            "id": "track-3",
            "title": "测试歌曲",
            "file_path": "test3.mp3",
            "artist_name": "A",
            "album_name": "B",
            "track_number": 1,
        })
        
        # 创建多个标签并添加
        tag1 = service.create_tag("标签1")
        tag2 = service.create_tag("标签2")
        service.add_tag_to_track("track-3", tag1.id)
        service.add_tag_to_track("track-3", tag2.id)
        
        tags = service.get_track_tags("track-3")
        
        assert len(tags) == 2
    
    def test_get_tracks_by_tag(self):
        """测试获取标签下的所有曲目"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # 创建多个曲目
        for i in range(3):
            self.db.insert("tracks", {
                "id": f"track-{i+10}",
                "title": f"歌曲{i+1}",
                "file_path": f"song{i+10}.mp3",
                "artist_name": "A",
                "album_name": "B",
                "track_number": i+1,
            })
        
        # 创建标签并添加到曲目
        tag = service.create_tag("共同标签")
        service.add_tag_to_track("track-10", tag.id)
        service.add_tag_to_track("track-11", tag.id)
        
        track_ids = service.get_tracks_by_tag(tag.id)
        
        assert len(track_ids) == 2
        assert "track-10" in track_ids
        assert "track-11" in track_ids
    
    def test_set_track_tags(self):
        """测试批量设置曲目标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # 创建曲目
        self.db.insert("tracks", {
            "id": "track-20",
            "title": "测试歌曲",
            "file_path": "test20.mp3",
            "artist_name": "A",
            "album_name": "B",
            "track_number": 1,
        })
        
        # 创建标签
        tag1 = service.create_tag("新标签1")
        tag2 = service.create_tag("新标签2")
        tag3 = service.create_tag("新标签3")
        
        # 先添加一个标签
        service.add_tag_to_track("track-20", tag1.id)
        
        # 批量设置（应该替换所有）
        result = service.set_track_tags("track-20", [tag2.id, tag3.id])
        
        assert result is True
        
        tags = service.get_track_tags("track-20")
        tag_names = [t.name for t in tags]
        
        assert len(tags) == 2
        assert "新标签1" not in tag_names
        assert "新标签2" in tag_names
        assert "新标签3" in tag_names
    
    def test_search_tags(self):
        """测试搜索标签"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        service.create_tag("摇滚音乐")
        service.create_tag("流行音乐")
        service.create_tag("古典")
        
        results = service.search_tags("音乐")
        
        assert len(results) == 2
    
    def test_get_tag_count(self):
        """测试获取标签总数"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        service.create_tag("标签A")
        service.create_tag("标签B")
        
        count = service.get_tag_count()
        
        assert count == 2
    
    def test_cascade_delete(self):
        """测试删除标签时级联删除关联"""
        from services.tag_service import TagService
        
        service = TagService(self.db)
        
        # 创建曲目和标签
        self.db.insert("tracks", {
            "id": "track-30",
            "title": "测试歌曲",
            "file_path": "test30.mp3",
            "artist_name": "A",
            "album_name": "B",
            "track_number": 1,
        })
        
        tag = service.create_tag("将被删除")
        service.add_tag_to_track("track-30", tag.id)
        
        # 删除标签
        service.delete_tag(tag.id)
        
        # 关联应该也被删除
        tags = service.get_track_tags("track-30")
        assert len(tags) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
