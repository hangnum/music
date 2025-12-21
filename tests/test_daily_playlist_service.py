"""
DailyPlaylistService Unit Tests
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List

from services.daily_playlist_service import DailyPlaylistService, DailyPlaylistResult
from models.track import Track


def _make_track(track_id: str, title: str = "Track") -> Track:
    """Create a Track object for testing."""
    return Track(id=track_id, title=f"{title} {track_id}", file_path=f"/path/to/{track_id}.mp3")


class TestDailyPlaylistResult:
    """Tests for DailyPlaylistResult."""
    
    def test_total_returns_track_count(self):
        """Test that the total property returns the number of tracks."""
        result = DailyPlaylistResult(tracks=[_make_track("1"), _make_track("2")])
        assert result.total == 2
    
    def test_summary_with_all_sources(self):
        """Test that the summary property includes all sources."""
        result = DailyPlaylistResult(
            tracks=[_make_track("1")],
            matched_by_tags=5,
            matched_by_semantic=3,
            filled_random=2,
        )
        summary = result.summary
        assert "Tag match 5 tracks" in summary
        assert "Semantic expansion 3 tracks" in summary
        assert "Random supplement 2 tracks" in summary
    
    def test_summary_with_no_matches(self):
        """Test the summary property when there are no matches."""
        result = DailyPlaylistResult()
        assert result.summary == "No matching results"


class TestDailyPlaylistService:
    """Tests for DailyPlaylistService."""
    
    def setup_method(self):
        """Setup before each test."""
        self.mock_tag_service = Mock()
        self.mock_library_service = Mock()
        self.mock_llm_provider = Mock()
        
        self.service = DailyPlaylistService(
            tag_service=self.mock_tag_service,
            library_service=self.mock_library_service,
            llm_provider=self.mock_llm_provider,
        )
    
    def test_generate_with_sufficient_tags(self):
        """Test generation when direct tag matching yields enough tracks."""
        # Mock tag matching to return enough tracks
        track_ids = [f"track_{i}" for i in range(50)]
        tracks = [_make_track(id) for id in track_ids]
        
        self.mock_tag_service.get_tracks_by_tags.return_value = track_ids
        self.mock_library_service.get_tracks_by_ids.return_value = tracks
        
        result = self.service.generate(["Pop"], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 50
        assert result.matched_by_semantic == 0
        assert result.filled_random == 0
        
        # LLM expansion should not be called
        self.mock_llm_provider.chat_completions.assert_not_called()
    
    def test_generate_with_semantic_expansion(self):
        """Test generation when LLM semantic expansion is needed."""
        # Direct tag matching returns only 20 tracks
        initial_ids = [f"track_{i}" for i in range(20)]
        initial_tracks = [_make_track(id) for id in initial_ids]
        
        # Semantic expansion returns an additional 30 tracks
        expanded_ids = [f"track_{i}" for i in range(20, 50)]
        expanded_tracks = [_make_track(id) for id in expanded_ids]
        
        # Set up mock behavior
        self.mock_tag_service.get_tracks_by_tags.side_effect = [
            initial_ids,  # First call: direct tag matching
            expanded_ids,  # Second call: matching after semantic expansion
        ]
        self.mock_library_service.get_tracks_by_ids.side_effect = [
            initial_tracks,
            expanded_tracks,
        ]
        self.mock_tag_service.get_all_tag_names.return_value = ["Pop", "Relax", "Classical", "Rock"]
        
        # Mock LLM to return semantically expanded tags
        self.mock_llm_provider.chat_completions.return_value = '{"expanded_tags": ["Relax", "Classical"], "reason": "Semantically close"}'
        
        result = self.service.generate(["Pop"], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 20
        assert result.matched_by_semantic == 30
        assert result.filled_random == 0
        assert "Relax" in result.expanded_tags or "Classical" in result.expanded_tags
    
    def test_generate_with_random_fallback(self):
        """Test generation when random supplement is needed."""
        # Tag matching returns only 10 tracks
        tag_ids = [f"track_{i}" for i in range(10)]
        tag_tracks = [_make_track(id) for id in tag_ids]
        
        # Tracks for random supplement
        random_tracks = [_make_track(f"random_{i}") for i in range(40)]
        
        self.mock_tag_service.get_tracks_by_tags.return_value = tag_ids
        self.mock_library_service.get_tracks_by_ids.return_value = tag_tracks
        self.mock_tag_service.get_all_tag_names.return_value = []  # No more tags to expand
        self.mock_library_service.query_tracks.return_value = random_tracks
        
        result = self.service.generate(["Pop"], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 10
        assert result.filled_random == 40
    
    def test_generate_no_llm_provider(self):
        """Test skipping directly to random supplement when no LLM provider is available."""
        service = DailyPlaylistService(
            tag_service=self.mock_tag_service,
            library_service=self.mock_library_service,
            llm_provider=None,  # No LLM
        )
        
        # Tag matching returns only 10 tracks
        tag_ids = [f"track_{i}" for i in range(10)]
        tag_tracks = [_make_track(id) for id in tag_ids]
        random_tracks = [_make_track(f"random_{i}") for i in range(40)]
        
        self.mock_tag_service.get_tracks_by_tags.return_value = tag_ids
        self.mock_library_service.get_tracks_by_ids.return_value = tag_tracks
        self.mock_library_service.query_tracks.return_value = random_tracks
        
        result = service.generate(["Pop"], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 10
        assert result.matched_by_semantic == 0
        assert result.filled_random == 40
    
    def test_deduplication(self):
        """Test deduplication logic."""
        # Tag matching returns duplicate track IDs
        tag_ids = ["track_1", "track_2", "track_1", "track_2"]
        tracks = [_make_track("track_1"), _make_track("track_2")]
        
        self.mock_tag_service.get_tracks_by_tags.return_value = tag_ids
        self.mock_library_service.get_tracks_by_ids.return_value = tracks
        self.mock_tag_service.get_all_tag_names.return_value = []
        
        # Random supplement might also contain duplicates
        random_tracks = [_make_track("track_1")] + [_make_track(f"random_{i}") for i in range(10)]
        self.mock_library_service.query_tracks.return_value = random_tracks
        
        result = self.service.generate(["Pop"], limit=10, shuffle=False)
        
        # Verify no duplicates
        track_ids = [t.id for t in result.tracks]
        assert len(track_ids) == len(set(track_ids))
    
    def test_empty_tags_uses_random_only(self):
        """Test using only random tracks when no tags are provided."""
        random_tracks = [_make_track(f"random_{i}") for i in range(50)]
        self.mock_library_service.query_tracks.return_value = random_tracks
        
        result = self.service.generate([], limit=50, shuffle=False)
        
        assert result.total == 50
        assert result.matched_by_tags == 0
        assert result.matched_by_semantic == 0
        assert result.filled_random == 50
        
        # Tag service should not be called
        self.mock_tag_service.get_tracks_by_tags.assert_not_called()


class TestLLMTagExpansion:
    """Tests for LLM tag expansion."""
    
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
        """Test that invalid tags returned by LLM are filtered out."""
        self.mock_tag_service.get_all_tag_names.return_value = ["Pop", "Rock", "Classical"]
        
        # LLM returns some invalid tags
        self.mock_llm_provider.chat_completions.return_value = '''
        {"expanded_tags": ["Pop", "Invalid Tag", "Rock"], "reason": "Test"}
        '''
        
        expanded = self.service._expand_tags_with_llm(["Classical"])
        
        # Should only contain valid tags
        assert "Pop" in expanded
        assert "Rock" in expanded
        assert "Invalid Tag" not in expanded
    
    def test_expand_tags_handles_json_error(self):
        """Test handling of non-JSON responses from LLM."""
        self.mock_tag_service.get_all_tag_names.return_value = ["Pop"]
        
        # LLM returns invalid JSON
        self.mock_llm_provider.chat_completions.return_value = "This is not JSON"
        
        expanded = self.service._expand_tags_with_llm(["Classical"])
        
        # Should return an empty list
        assert expanded == []
    
    def test_expand_tags_handles_exception(self):
        """Test handling of exceptions during LLM calls."""
        self.mock_tag_service.get_all_tag_names.return_value = ["Pop"]
        
        # LLM call raises an exception
        self.mock_llm_provider.chat_completions.side_effect = Exception("API Error")
        
        expanded = self.service._expand_tags_with_llm(["Classical"])
        
        # Should return an empty list instead of raising an exception
        assert expanded == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
