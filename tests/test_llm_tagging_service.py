"""
LLM 批量标注服务测试
"""

import pytest
import os

from core.database import DatabaseManager
from services.tag_service import TagService
from services.llm_tagging_service import LLMTaggingService, TaggingJobStatus


class _FakeClient:
    """模拟 LLM 客户端"""
    def __init__(self, response: str):
        self._response = response
        self.call_count = 0
    
    def chat_completions(self, _messages):
        self.call_count += 1
        return self._response


class _FakeLibrary:
    """模拟 LibraryService"""
    def __init__(self, tracks):
        self._tracks = list(tracks)
        self._id_map = {t.id: t for t in tracks}
    
    def get_tracks_by_ids(self, ids):
        return [self._id_map[i] for i in ids if i in self._id_map]


class _MockTrack:
    """模拟 Track 对象"""
    def __init__(self, id, title="", artist_name="", album_name="", genre=""):
        self.id = id
        self.title = title
        self.artist_name = artist_name
        self.album_name = album_name
        self.genre = genre


class TestLLMTaggingService:
    """LLM 批量标注服务测试"""
    
    def setup_method(self):
        from services.config_service import ConfigService
        ConfigService.reset_instance()
        DatabaseManager.reset_instance()
        self.db = DatabaseManager("test_llm_tagging.db")
        self.tag_service = TagService(self.db)
        self.config = ConfigService("config/does_not_exist.yaml")
    
    def teardown_method(self):
        from services.config_service import ConfigService
        ConfigService.reset_instance()
        DatabaseManager.reset_instance()
        if os.path.exists("test_llm_tagging.db"):
            os.remove("test_llm_tagging.db")
    
    def _create_tracks(self, count: int):
        """创建测试曲目"""
        tracks = []
        for i in range(count):
            track_id = f"track-{i}"
            self.db.insert("tracks", {
                "id": track_id,
                "title": f"Song {i}",
                "file_path": f"song{i}.mp3",
                "artist_name": f"Artist {i % 3}",
                "album_name": f"Album {i % 2}",
                "genre": "Pop" if i % 2 == 0 else "Rock",
            })
            tracks.append(_MockTrack(
                id=track_id,
                title=f"Song {i}",
                artist_name=f"Artist {i % 3}",
                album_name=f"Album {i % 2}",
                genre="Pop" if i % 2 == 0 else "Rock",
            ))
        return tracks
    
    def test_start_tagging_job_returns_job_id(self):
        """测试启动标注任务返回任务 ID"""
        tracks = self._create_tracks(3)
        library = _FakeLibrary(tracks)
        
        response = '{"tags": {"track-0": ["Pop", "Artist 0"], "track-1": ["Rock"], "track-2": ["Pop"]}}'
        client = _FakeClient(response)
        
        service = LLMTaggingService(
            config=self.config,
            db=self.db,
            tag_service=self.tag_service,
            library_service=library,
            client=client,
        )
        
        job_id = service.start_tagging_job(batch_size=10)
        
        assert job_id != ""
        assert client.call_count >= 1
    
    def test_tagging_job_creates_tags(self):
        """测试标注任务创建标签"""
        tracks = self._create_tracks(2)
        library = _FakeLibrary(tracks)
        
        response = '{"tags": {"track-0": ["流行", "中文"], "track-1": ["摇滚", "英文"]}}'
        client = _FakeClient(response)
        
        service = LLMTaggingService(
            config=self.config,
            db=self.db,
            tag_service=self.tag_service,
            library_service=library,
            client=client,
        )
        
        service.start_tagging_job(batch_size=10)
        
        # 验证标签已创建
        tags = self.tag_service.get_all_tags()
        tag_names = [t.name for t in tags]
        
        assert "流行" in tag_names
        assert "中文" in tag_names
        assert "摇滚" in tag_names
        assert "英文" in tag_names
    
    def test_tagging_job_associates_tags_with_tracks(self):
        """测试标注任务关联标签到曲目"""
        tracks = self._create_tracks(2)
        library = _FakeLibrary(tracks)
        
        response = '{"tags": {"track-0": ["流行"], "track-1": ["摇滚"]}}'
        client = _FakeClient(response)
        
        service = LLMTaggingService(
            config=self.config,
            db=self.db,
            tag_service=self.tag_service,
            library_service=library,
            client=client,
        )
        
        service.start_tagging_job(batch_size=10)
        
        # 验证曲目标签关联
        track0_tags = self.tag_service.get_track_tag_names("track-0")
        track1_tags = self.tag_service.get_track_tag_names("track-1")
        
        assert "流行" in track0_tags
        assert "摇滚" in track1_tags
    
    def test_get_job_status(self):
        """测试获取任务状态"""
        tracks = self._create_tracks(2)
        library = _FakeLibrary(tracks)
        
        response = '{"tags": {"track-0": ["Pop"], "track-1": ["Rock"]}}'
        client = _FakeClient(response)
        
        service = LLMTaggingService(
            config=self.config,
            db=self.db,
            tag_service=self.tag_service,
            library_service=library,
            client=client,
        )
        
        job_id = service.start_tagging_job(batch_size=10)
        status = service.get_job_status(job_id)
        
        assert status is not None
        assert status.job_id == job_id
        assert status.status == "completed"
        assert status.total_tracks == 2
        assert status.processed_tracks == 2
    
    def test_tagging_job_marks_tracks_as_tagged(self):
        """测试标注任务标记曲目为已标注"""
        tracks = self._create_tracks(2)
        library = _FakeLibrary(tracks)
        
        response = '{"tags": {"track-0": ["Pop"], "track-1": ["Rock"]}}'
        client = _FakeClient(response)
        
        service = LLMTaggingService(
            config=self.config,
            db=self.db,
            tag_service=self.tag_service,
            library_service=library,
            client=client,
        )
        
        service.start_tagging_job(batch_size=10)
        
        # 验证未标注曲目列表为空
        untagged = self.tag_service.get_untagged_tracks(source="llm")
        assert len(untagged) == 0
    
    def test_tagging_skips_already_tagged_tracks(self):
        """测试跳过已标注曲目"""
        tracks = self._create_tracks(3)
        library = _FakeLibrary(tracks)
        
        # 手动标记一个曲目为已标注
        self.tag_service.mark_track_as_tagged("track-0")
        
        response = '{"tags": {"track-1": ["Rock"], "track-2": ["Pop"]}}'
        client = _FakeClient(response)
        
        service = LLMTaggingService(
            config=self.config,
            db=self.db,
            tag_service=self.tag_service,
            library_service=library,
            client=client,
        )
        
        job_id = service.start_tagging_job(batch_size=10)
        status = service.get_job_status(job_id)
        
        # 应该只处理 2 个曲目
        assert status.total_tracks == 2
    
    def test_get_tagging_stats(self):
        """测试获取标注统计信息"""
        tracks = self._create_tracks(3)
        library = _FakeLibrary(tracks)
        
        response = '{"tags": {"track-0": ["Pop"], "track-1": ["Rock"], "track-2": ["Jazz"]}}'
        client = _FakeClient(response)
        
        service = LLMTaggingService(
            config=self.config,
            db=self.db,
            tag_service=self.tag_service,
            library_service=library,
            client=client,
        )
        
        service.start_tagging_job(batch_size=10)
        stats = service.get_tagging_stats()
        
        assert stats["tagged_tracks"] == 3
        assert stats["total_tracks"] == 3
        assert stats["llm_tags"] == 3  # Pop, Rock, Jazz
    
    def test_progress_callback_called(self):
        """测试进度回调被调用"""
        tracks = self._create_tracks(5)
        library = _FakeLibrary(tracks)
        
        response = '{"tags": {}}'
        client = _FakeClient(response)
        
        service = LLMTaggingService(
            config=self.config,
            db=self.db,
            tag_service=self.tag_service,
            library_service=library,
            client=client,
        )
        
        progress_calls = []
        def progress_callback(current, total):
            progress_calls.append((current, total))
        
        service.start_tagging_job(batch_size=2, progress_callback=progress_callback)
        
        assert len(progress_calls) > 0
        # 最后一次调用应该是完成
        assert progress_calls[-1][0] == progress_calls[-1][1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
