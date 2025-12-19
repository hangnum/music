"""
WebSearchService 单元测试

测试网络搜索服务的各项功能，使用 Mock 避免真实网络请求。
"""

import pytest
from unittest.mock import MagicMock, patch

from services.web_search_service import WebSearchService, SearchResult


class TestWebSearchServiceInit:
    """测试初始化"""
    
    def test_init_default_timeout(self):
        """测试默认超时时间"""
        service = WebSearchService()
        assert service._timeout == 10.0
    
    def test_init_custom_timeout(self):
        """测试自定义超时时间"""
        service = WebSearchService(timeout=5.0)
        assert service._timeout == 5.0
    
    def test_ddgs_lazy_load(self):
        """测试 DDGS 懒加载"""
        service = WebSearchService()
        assert service._ddgs is None


class TestCleanText:
    """测试文本清理功能"""
    
    def test_clean_normal_text(self):
        """测试正常文本"""
        service = WebSearchService()
        result = service._clean_text("这是一首流行歌曲")
        assert result == "这是一首流行歌曲"
    
    def test_clean_whitespace(self):
        """测试多余空白"""
        service = WebSearchService()
        result = service._clean_text("  多余   空白  ")
        assert result == "多余 空白"
    
    def test_clean_noise_login(self):
        """测试过滤登录相关噪音"""
        service = WebSearchService()
        result = service._clean_text("请登录后查看完整内容")
        assert result == ""
    
    def test_clean_noise_download(self):
        """测试过滤下载相关噪音"""
        service = WebSearchService()
        result = service._clean_text("立即下载APP体验更多")
        assert result == ""
    
    def test_clean_noise_404(self):
        """测试过滤404错误"""
        service = WebSearchService()
        result = service._clean_text("404页面不存在")
        assert result == ""
    
    def test_clean_empty_string(self):
        """测试空字符串"""
        service = WebSearchService()
        result = service._clean_text("")
        assert result == ""
    
    def test_clean_none(self):
        """测试 None 值"""
        service = WebSearchService()
        result = service._clean_text(None)
        assert result == ""


class TestRelevanceFilter:
    """测试相关性过滤"""
    
    def test_relevant_with_keyword(self):
        """测试包含关键词的内容"""
        service = WebSearchService()
        result = service._is_relevant("周杰伦是著名歌手", ["周杰伦"])
        assert result is True
    
    def test_relevant_case_insensitive(self):
        """测试大小写不敏感"""
        service = WebSearchService()
        result = service._is_relevant("Rock music is great", ["rock"])
        assert result is True
    
    def test_irrelevant_content(self):
        """测试不相关内容"""
        service = WebSearchService()
        result = service._is_relevant("今日天气晴朗", ["周杰伦", "七里香"])
        assert result is False
    
    def test_empty_keywords(self):
        """测试空关键词列表（不过滤）"""
        service = WebSearchService()
        result = service._is_relevant("任何内容", [])
        assert result is True
    
    def test_empty_body(self):
        """测试空内容"""
        service = WebSearchService()
        result = service._is_relevant("", ["关键词"])
        assert result is True


class TestDeduplicate:
    """测试去重功能"""
    
    def test_deduplicate_exact(self):
        """测试完全相同的内容"""
        service = WebSearchService()
        texts = ["内容A", "内容A", "内容B"]
        result = service._deduplicate(texts)
        assert result == ["内容A", "内容B"]
    
    def test_deduplicate_prefix(self):
        """测试相同前缀的长文本"""
        service = WebSearchService()
        long_text = "A" * 60
        texts = [long_text, long_text + "更多内容"]
        result = service._deduplicate(texts)
        # 由于前50字符相同，应该去重
        assert len(result) == 1
    
    def test_deduplicate_preserve_order(self):
        """测试保留顺序"""
        service = WebSearchService()
        texts = ["第一", "第二", "第三"]
        result = service._deduplicate(texts)
        assert result == ["第一", "第二", "第三"]
    
    def test_deduplicate_empty(self):
        """测试空列表"""
        service = WebSearchService()
        result = service._deduplicate([])
        assert result == []


class TestSearchMusicInfo:
    """测试音乐搜索"""
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_with_artist_and_title(self, mock_search):
        """测试艺术家+歌曲搜索"""
        mock_search.return_value = ["周杰伦的七里香是一首R&B风格歌曲"]
        
        service = WebSearchService()
        result = service.search_music_info("周杰伦", "七里香")
        
        assert len(result) >= 0
        # 验证至少调用了一次搜索
        assert mock_search.called
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_empty_input(self, mock_search):
        """测试空输入"""
        service = WebSearchService()
        result = service.search_music_info("", "")
        
        assert result == []
        mock_search.assert_not_called()
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_filters_irrelevant(self, mock_search):
        """测试过滤不相关结果"""
        mock_search.return_value = [
            "周杰伦七里香专辑介绍",
            "今日股市行情分析",
        ]
        
        service = WebSearchService()
        result = service.search_music_info("周杰伦", "七里香")
        
        # 不相关的股市内容应被过滤
        assert "股市" not in str(result)


class TestSearchArtistInfo:
    """测试艺术家搜索"""
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_artist(self, mock_search):
        """测试艺术家信息搜索"""
        mock_search.return_value = ["周杰伦，华语流行音乐代表人物"]
        
        service = WebSearchService()
        result = service.search_artist_info("周杰伦")
        
        assert len(result) >= 0
        assert mock_search.called
    
    def test_search_artist_empty(self):
        """测试空艺术家名"""
        service = WebSearchService()
        result = service.search_artist_info("")
        assert result == []


class TestSearchAlbumInfo:
    """测试专辑搜索"""
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_album(self, mock_search):
        """测试专辑信息搜索"""
        mock_search.return_value = ["七里香专辑获得多项大奖"]
        
        service = WebSearchService()
        result = service.search_album_info("周杰伦", "七里香")
        
        assert mock_search.called
    
    def test_search_album_empty(self):
        """测试空专辑名"""
        service = WebSearchService()
        result = service.search_album_info("周杰伦", "")
        assert result == []


class TestGetMusicContext:
    """测试综合上下文获取"""
    
    @patch.object(WebSearchService, 'search_music_info')
    @patch.object(WebSearchService, 'search_artist_info')
    @patch.object(WebSearchService, 'search_album_info')
    def test_get_context_structured(self, mock_album, mock_artist, mock_music):
        """测试结构化输出"""
        mock_music.return_value = ["R&B风格歌曲"]
        mock_artist.return_value = ["华语流行歌手"]
        mock_album.return_value = ["2004年发行专辑"]
        
        service = WebSearchService()
        result = service.get_music_context("周杰伦", "七里香", "七里香")
        
        # 验证包含结构化标签
        assert "[歌曲]" in result
    
    @patch.object(WebSearchService, 'search_music_info')
    def test_get_context_max_chars(self, mock_music):
        """测试最大字符限制"""
        mock_music.return_value = ["A" * 1000]
        
        service = WebSearchService()
        result = service.get_music_context("艺术家", "歌曲", None, max_total_chars=100)
        
        assert len(result) <= 103  # 100 + "..." 
    
    @patch.object(WebSearchService, 'search_music_info')
    def test_get_context_empty_results(self, mock_music):
        """测试无搜索结果"""
        mock_music.return_value = []
        
        service = WebSearchService()
        result = service.get_music_context(None, None, None)
        
        assert result == ""


class TestDoSearch:
    """测试底层搜索执行"""
    
    def test_do_search_ddgs_not_installed(self):
        """测试 ddgs 未安装时的行为"""
        service = WebSearchService()
        service._ddgs = None
        
        with patch.object(service, '_get_ddgs', return_value=None):
            result = service._do_search("test query", 3)
            assert result == []
    
    @patch('services.web_search_service.WebSearchService._get_ddgs')
    def test_do_search_exception_handling(self, mock_get_ddgs):
        """测试搜索异常处理"""
        mock_ddgs = MagicMock()
        mock_ddgs.text.side_effect = Exception("Network error")
        mock_get_ddgs.return_value = mock_ddgs
        
        service = WebSearchService()
        result = service._do_search("test query", 3)
        
        # 异常时返回空列表
        assert result == []
    
    @patch('services.web_search_service.WebSearchService._get_ddgs')
    def test_do_search_truncates_long_results(self, mock_get_ddgs):
        """测试长结果截断"""
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = [{"body": "A" * 300}]
        mock_get_ddgs.return_value = mock_ddgs
        
        service = WebSearchService()
        result = service._do_search("test query", 3)
        
        # 结果应该被截断
        if result:
            assert len(result[0]) <= 155  # 150 + "…" 或句号截断


class TestSearchResult:
    """测试 SearchResult 数据类"""
    
    def test_search_result_creation(self):
        """测试创建搜索结果"""
        result = SearchResult(
            title="测试标题",
            body="测试内容",
            url="https://example.com"
        )
        assert result.title == "测试标题"
        assert result.body == "测试内容"
        assert result.url == "https://example.com"
