"""
DailyPlaylistService 单元测试
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List

from services.daily_playlist_service import DailyPlaylistService, DailyPlaylistResult
from models.track import Track


def _make_track(id: str, title: str = "Track") -> Track:
    """创建测试用 Track 对象"""
    return Track(id=id, title=f"{title} {id}", file_path=f"/path/to/{id}.mp3")


class TestDailyPlaylistResult:
    """DailyPlaylistResult 测试"""
    
    def test_total_returns_track_count(self):
        """测试 total 属性返回曲目数量"""
        result = DailyPlaylistResult(tracks=[_make_track("1"), _make_track("2")])
        assert result.total == 2
    
    def test_summary_with_all_sources(self):
        """测试 summary 属性包含所有来源"""
        result = DailyPlaylistResult(
            tracks=[_make_track("1")],
            matched_by_tags=5,
            matched_by_semantic=3,
            filled_random=2,
        )
        summary = result.summary
        assert "标签匹配 5 首" in summary
        assert "语义扩展 3 首" in summary
        assert "随机补充 2 首" in summary
    
    def test_summary_with_no_matches(self):
        """测试无匹配时的 summary"""
        result = DailyPlaylistResult()
        assert result.summary == "无匹配结果"


class TestDailyPlaylistService:
    """DailyPlaylistService 测试"""
    
    def setup_method(self):
        """测试准备"""
        self.mock_tag_service = Mock()
        self.mock_library_service = Mock()
        self.mock_llm_provider = Mock()
        
        self.service = DailyPlaylistService(
            tag_service=self.mock_tag_service,
            library_service=self.mock_library_service,
            llm_provider=self.mock_llm_provider,
        )
    
    def test_generate_with_sufficient_tags(self):
        """测试标签直接匹配足够时的情况"""
        # 模拟标签匹配返回足够的曲目
        track_ids = [f"track_{i}" for i in range(50)]
        tracks = [_make_track(id) for id in track_ids]
        
        self.mock_tag_service.get_tracks_by_tags.return_value = track_ids
        self.mock_library_service.get_tracks_by_ids.return_value = tracks
        
        result = self.service.generate(["流行"], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 50
        assert result.matched_by_semantic == 0
        assert result.filled_random == 0
        
        # 不应调用 LLM 扩展
        self.mock_llm_provider.chat_completions.assert_not_called()
    
    def test_generate_with_semantic_expansion(self):
        """测试需要 LLM 语义扩展的情况"""
        # 直接标签匹配只返回 20 首
        initial_ids = [f"track_{i}" for i in range(20)]
        initial_tracks = [_make_track(id) for id in initial_ids]
        
        # 语义扩展额外返回 30 首
        expanded_ids = [f"track_{i}" for i in range(20, 50)]
        expanded_tracks = [_make_track(id) for id in expanded_ids]
        
        # 设置 mock 行为
        self.mock_tag_service.get_tracks_by_tags.side_effect = [
            initial_ids,  # 第一次调用：直接标签匹配
            expanded_ids,  # 第二次调用：语义扩展后的标签匹配
        ]
        self.mock_library_service.get_tracks_by_ids.side_effect = [
            initial_tracks,
            expanded_tracks,
        ]
        self.mock_tag_service.get_all_tag_names.return_value = ["流行", "轻松", "古典", "摇滚"]
        
        # 模拟 LLM 返回语义扩展的标签
        self.mock_llm_provider.chat_completions.return_value = '{"expanded_tags": ["轻松", "古典"], "reason": "语义相近"}'
        
        result = self.service.generate(["流行"], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 20
        assert result.matched_by_semantic == 30
        assert result.filled_random == 0
        assert "轻松" in result.expanded_tags or "古典" in result.expanded_tags
    
    def test_generate_with_random_fallback(self):
        """测试需要随机补充的情况"""
        # 标签匹配只返回 10 首
        tag_ids = [f"track_{i}" for i in range(10)]
        tag_tracks = [_make_track(id) for id in tag_ids]
        
        # 随机补充的曲目
        random_tracks = [_make_track(f"random_{i}") for i in range(40)]
        
        self.mock_tag_service.get_tracks_by_tags.return_value = tag_ids
        self.mock_library_service.get_tracks_by_ids.return_value = tag_tracks
        self.mock_tag_service.get_all_tag_names.return_value = []  # 没有更多标签可扩展
        self.mock_library_service.query_tracks.return_value = random_tracks
        
        result = self.service.generate(["流行"], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 10
        assert result.filled_random == 40
    
    def test_generate_no_llm_provider(self):
        """测试无 LLM Provider 时直接跳到随机补充"""
        service = DailyPlaylistService(
            tag_service=self.mock_tag_service,
            library_service=self.mock_library_service,
            llm_provider=None,  # 无 LLM
        )
        
        # 标签匹配只返回 10 首
        tag_ids = [f"track_{i}" for i in range(10)]
        tag_tracks = [_make_track(id) for id in tag_ids]
        random_tracks = [_make_track(f"random_{i}") for i in range(40)]
        
        self.mock_tag_service.get_tracks_by_tags.return_value = tag_ids
        self.mock_library_service.get_tracks_by_ids.return_value = tag_tracks
        self.mock_library_service.query_tracks.return_value = random_tracks
        
        result = service.generate(["流行"], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 10
        assert result.matched_by_semantic == 0
        assert result.filled_random == 40
    
    def test_deduplication(self):
        """测试去重逻辑"""
        # 标签匹配返回重复的曲目 ID
        tag_ids = ["track_1", "track_2", "track_1", "track_2"]
        tracks = [_make_track("track_1"), _make_track("track_2")]
        
        self.mock_tag_service.get_tracks_by_tags.return_value = tag_ids
        self.mock_library_service.get_tracks_by_ids.return_value = tracks
        self.mock_tag_service.get_all_tag_names.return_value = []
        
        # 随机补充也可能有重复
        random_tracks = [_make_track("track_1")] + [_make_track(f"random_{i}") for i in range(10)]
        self.mock_library_service.query_tracks.return_value = random_tracks
        
        result = self.service.generate(["流行"], limit=10, shuffle=False)
        
        # 验证没有重复
        track_ids = [t.id for t in result.tracks]
        assert len(track_ids) == len(set(track_ids))
    
    def test_empty_tags_uses_random_only(self):
        """测试空标签时只使用随机"""
        random_tracks = [_make_track(f"random_{i}") for i in range(50)]
        self.mock_library_service.query_tracks.return_value = random_tracks
        
        result = self.service.generate([], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 0
        assert result.matched_by_semantic == 0
        assert result.filled_random == 50
        
        # 不应调用标签服务
        self.mock_tag_service.get_tracks_by_tags.assert_not_called()


class TestLLMTagExpansion:
    """LLM 标签扩展测试"""
    
    def setup_method(self):
        self.mock_tag_service = Mock()
        self.mock_library_service = Mock()
        self.mock_llm_provider = Mock()
        
        self.service = DailyPlaylistService(
            tag_service=self.mock_tag_service,
            library_service=self.mock_library_service,
            llm_provider=self.mock_llm_provider,
        )
    
    def test_expand_tags_filters_invalid(self):
        """测试 LLM 返回的无效标签被过滤"""
        self.mock_tag_service.get_all_tag_names.return_value = ["流行", "摇滚", "古典"]
        
        # LLM 返回包含无效标签
        self.mock_llm_provider.chat_completions.return_value = '''
        {"expanded_tags": ["流行", "不存在的标签", "摇滚"], "reason": "测试"}
        '''
        
        expanded = self.service._expand_tags_with_llm(["古典"])
        
        # 只应包含有效标签
        assert "流行" in expanded
        assert "摇滚" in expanded
        assert "不存在的标签" not in expanded
    
    def test_expand_tags_handles_json_error(self):
        """测试 LLM 返回非 JSON 时的处理"""
        self.mock_tag_service.get_all_tag_names.return_value = ["流行"]
        
        # LLM 返回无效 JSON
        self.mock_llm_provider.chat_completions.return_value = "这不是 JSON"
        
        expanded = self.service._expand_tags_with_llm(["古典"])
        
        # 应返回空列表
        assert expanded == []
    
    def test_expand_tags_handles_exception(self):
        """测试 LLM 调用异常时的处理"""
        self.mock_tag_service.get_all_tag_names.return_value = ["流行"]
        
        # LLM 调用抛出异常
        self.mock_llm_provider.chat_completions.side_effect = Exception("API Error")
        
        expanded = self.service._expand_tags_with_llm(["古典"])
        
        # 应返回空列表而不是抛出异常
        assert expanded == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
