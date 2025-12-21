"""
WebSearchService Unit Tests

Tests for various web search service functionalities using Mocks to avoid real network requests.
"""

import pytest
from unittest.mock import MagicMock, patch

from services.web_search_service import WebSearchService, SearchResult


class TestWebSearchServiceInit:
    """Tests for initialization."""
    
    def test_init_default_timeout(self):
        """Test default timeout period."""
        service = WebSearchService()
        assert service._timeout == 10.0
    
    def test_init_custom_timeout(self):
        """Test custom timeout period."""
        service = WebSearchService(timeout=5.0)
        assert service._timeout == 5.0
    
    def test_ddgs_lazy_load(self):
        """Test lazy loading of the DDGS client."""
        service = WebSearchService()
        assert service._ddgs is None


class TestCleanText:
    """Tests for text cleaning functionality."""
    
    def test_clean_normal_text(self):
        """Test cleaning normal text."""
        service = WebSearchService()
        result = service._clean_text("This is a pop song")
        assert result == "This is a pop song"
    
    def test_clean_whitespace(self):
        """Test cleaning of extra whitespace."""
        service = WebSearchService()
        result = service._clean_text("  extra   whitespace  ")
        assert result == "extra whitespace"
    
    def test_clean_noise_login(self):
        """Test filtering login-related noise."""
        service = WebSearchService()
        result = service._clean_text("Please login to view full content")
        assert result == ""
    
    def test_clean_noise_download(self):
        """Test filtering download-related noise."""
        service = WebSearchService()
        result = service._clean_text("Download APP now for more experience")
        assert result == ""
    
    def test_clean_noise_404(self):
        """Test filtering 404 error noise."""
        service = WebSearchService()
        result = service._clean_text("404 Page not found")
        assert result == ""
    
    def test_clean_empty_string(self):
        """Test cleaning an empty string."""
        service = WebSearchService()
        result = service._clean_text("")
        assert result == ""
    
    def test_clean_none(self):
        """Test cleaning a None value."""
        service = WebSearchService()
        result = service._clean_text(None)
        assert result == ""


class TestRelevanceFilter:
    """Tests for relevance filtering."""
    
    def test_relevant_with_keyword(self):
        """Test relevance when keywords are present."""
        service = WebSearchService()
        result = service._is_relevant("Jay Chou is a famous singer", ["Jay Chou"])
        assert result is True
    
    def test_relevant_case_insensitive(self):
        """Test case-insensitive relevance matching."""
        service = WebSearchService()
        result = service._is_relevant("Rock music is great", ["rock"])
        assert result is True
    
    def test_irrelevant_content(self):
        """Test filtering irrelevant content."""
        service = WebSearchService()
        result = service._is_relevant("The weather is sunny today", ["Jay Chou", "Qi Li Xiang"])
        assert result is False
    
    def test_empty_keywords(self):
        """Test that empty keywords do not result in filtering."""
        service = WebSearchService()
        result = service._is_relevant("Any content", [])
        assert result is True
    
    def test_empty_body(self):
        """Test relevance check with empty body."""
        service = WebSearchService()
        result = service._is_relevant("", ["keyword"])
        assert result is True


class TestDeduplicate:
    """Tests for deduplication."""
    
    def test_deduplicate_exact(self):
        """Test deduplication of identical content."""
        service = WebSearchService()
        texts = ["Content A", "Content A", "Content B"]
        result = service._deduplicate(texts)
        assert result == ["Content A", "Content B"]
    
    def test_deduplicate_prefix(self):
        """Test deduplication based on long text prefix."""
        service = WebSearchService()
        long_text = "A" * 60
        texts = [long_text, long_text + " more content"]
        result = service._deduplicate(texts)
        # Should deduplicate because the first 50 characters match
        assert len(result) == 1
    
    def test_deduplicate_preserve_order(self):
        """Test that order is preserved during deduplication."""
        service = WebSearchService()
        texts = ["First", "Second", "Third"]
        result = service._deduplicate(texts)
        assert result == ["First", "Second", "Third"]
    
    def test_deduplicate_empty(self):
        """Test deduplication of an empty list."""
        service = WebSearchService()
        result = service._deduplicate([])
        assert result == []


class TestSearchMusicInfo:
    """Tests for music information search."""
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_with_artist_and_title(self, mock_search):
        """Test artist and title search."""
        mock_search.return_value = ["Jay Chou's Qi Li Xiang is an R&B style song"]
        
        service = WebSearchService()
        result = service.search_music_info("Jay Chou", "Qi Li Xiang")
        
        assert len(result) >= 0
        # Verify that search was called at least once
        assert mock_search.called
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_empty_input(self, mock_search):
        """Test search with empty input."""
        service = WebSearchService()
        result = service.search_music_info("", "")
        
        assert result == []
        mock_search.assert_not_called()
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_filters_irrelevant(self, mock_search):
        """Test filtering of irrelevant search results."""
        mock_search.return_value = [
            "Jay Chou Qi Li Xiang album introduction",
            "Today's stock market analysis",
        ]
        
        service = WebSearchService()
        result = service.search_music_info("Jay Chou", "Qi Li Xiang")
        
        # Stock market content should be filtered out
        assert "stock market" not in str(result)


class TestSearchArtistInfo:
    """Tests for artist information search."""
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_artist(self, mock_search):
        """Test artist info retrieval."""
        mock_search.return_value = ["Jay Chou, a representative figure of Chinese pop music"]
        
        service = WebSearchService()
        result = service.search_artist_info("Jay Chou")
        
        assert len(result) >= 0
        assert mock_search.called
    
    def test_search_artist_empty(self):
        """Test artist search with empty name."""
        service = WebSearchService()
        result = service.search_artist_info("")
        assert result == []


class TestSearchAlbumInfo:
    """Tests for album information search."""
    
    @patch.object(WebSearchService, '_do_search')
    def test_search_album(self, mock_search):
        """Test album info retrieval."""
        mock_search.return_value = ["Common Jasmine Orange album won multiple awards"]
        
        service = WebSearchService()
        result = service.search_album_info("Jay Chou", "Qi Li Xiang")
        
        assert mock_search.called
    
    def test_search_album_empty(self):
        """Test album search with empty name."""
        service = WebSearchService()
        result = service.search_album_info("Jay Chou", "")
        assert result == []


class TestGetMusicContext:
    """Tests for comprehensive context retrieval."""
    
    @patch.object(WebSearchService, 'search_music_info')
    @patch.object(WebSearchService, 'search_artist_info')
    @patch.object(WebSearchService, 'search_album_info')
    def test_get_context_structured(self, mock_album, mock_artist, mock_music):
        """Test structured output generation."""
        mock_music.return_value = ["R&B style song"]
        mock_artist.return_value = ["Chinese pop singer"]
        mock_album.return_value = ["Album released in 2004"]
        
        service = WebSearchService()
        result = service.get_music_context("Jay Chou", "Qi Li Xiang", "Qi Li Xiang")
        
        # Verify inclusion of structured tags
        assert "[Song]" in result
    
    @patch.object(WebSearchService, 'search_music_info')
    def test_get_context_max_chars(self, mock_music):
        """Test character limit for context."""
        mock_music.return_value = ["A" * 1000]
        
        service = WebSearchService()
        result = service.get_music_context("Artist", "Song", None, max_total_chars=100)
        
        assert len(result) <= 103  # 100 + "..." 
    
    @patch.object(WebSearchService, 'search_music_info')
    def test_get_context_empty_results(self, mock_music):
        """Test context retrieval with no results."""
        mock_music.return_value = []
        
        service = WebSearchService()
        result = service.get_music_context(None, None, None)
        
        assert result == ""


class TestDoSearch:
    """Tests for underlying search execution."""
    
    def test_do_search_ddgs_not_installed(self):
        """Test behavior when ddgs is not installed."""
        service = WebSearchService()
        service._ddgs = None
        
        with patch.object(service, '_get_ddgs', return_value=None):
            result = service._do_search("test query", 3)
            assert result == []
    
    @patch('services.web_search_service.WebSearchService._get_ddgs')
    def test_do_search_exception_handling(self, mock_get_ddgs):
        """Test exception handling during search."""
        mock_ddgs = MagicMock()
        mock_ddgs.text.side_effect = Exception("Network error")
        mock_get_ddgs.return_value = mock_ddgs
        
        service = WebSearchService()
        result = service._do_search("test query", 3)
        
        # Return empty list on exception
        assert result == []
    
    @patch('services.web_search_service.WebSearchService._get_ddgs')
    def test_do_search_truncates_long_results(self, mock_get_ddgs):
        """Test truncation of long search results."""
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = [{"body": "A" * 300}]
        mock_get_ddgs.return_value = mock_ddgs
        
        service = WebSearchService()
        result = service._do_search("test query", 3)
        
        # Result should be truncated
        if result:
            assert len(result[0]) <= 155  # 150 + "…" or truncated at period


class TestSearchResult:
    """Tests for the SearchResult data class."""
    
    def test_search_result_creation(self):
        """Test creation of search result."""
        result = SearchResult(
            title="Test Title",
            body="Test Content",
            url="https://example.com"
        )
        assert result.title == "Test Title"
        assert result.body == "Test Content"
        assert result.url == "https://example.com"
