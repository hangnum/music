"""
Tag Query Parser Tests
"""

import pytest

from services.tag_query_parser import TagQueryParser, TagQuery


class _FakeClient:
    """Mock LLM client."""
    def __init__(self, response: str):
        self._response = response
    
    def chat_completions(self, _messages):
        return self._response


class TestTagQuery:
    """Tests for the TagQuery data class."""
    
    def test_is_valid_with_tags(self):
        """Test that is_valid is True when tags are present."""
        query = TagQuery(tags=["Pop", "Rock"])
        assert query.is_valid is True
    
    def test_is_valid_without_tags(self):
        """Test that is_valid is False when no tags are present."""
        query = TagQuery(tags=[])
        assert query.is_valid is False
    
    def test_default_values(self):
        """Test default values of TagQuery."""
        query = TagQuery()
        assert query.tags == []
        assert query.match_mode == "any"
        assert query.confidence == 0.0
        assert query.reason == ""


class TestTagQueryParser:
    """Tests for TagQueryParser."""
    
    def test_parse_artist_query(self):
        """Test parsing an artist-based query."""
        response = '{"matched_tags": ["Jay Chou"], "match_mode": "any", "confidence": 0.9, "reason": "User wants to hear Jay Chou"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("I want to hear Jay Chou's songs", ["Jay Chou", "JJ Lin", "Pop"])
        
        assert result.is_valid
        assert "Jay Chou" in result.tags
        assert result.match_mode == "any"
        assert result.confidence >= 0.8
    
    def test_parse_genre_query(self):
        """Test parsing a genre-based query."""
        response = '{"matched_tags": ["Rock", "Energetic"], "match_mode": "any", "confidence": 0.85, "reason": "User wants to hear rock music"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("Give me some rock music", ["Pop", "Rock", "Classical", "Energetic", "Relaxing"])
        
        assert result.is_valid
        assert "Rock" in result.tags
    
    def test_parse_mood_query(self):
        """Test parsing a mood-based query."""
        response = '{"matched_tags": ["Relaxing", "Soft"], "match_mode": "all", "confidence": 0.75, "reason": "User wants relaxing music"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("Time to relax", ["Energetic", "Relaxing", "Soft", "Classical"])
        
        assert result.is_valid
        assert "Relaxing" in result.tags
    
    def test_parse_returns_empty_for_no_match(self):
        """Test that an empty query is returned when no tags match."""
        response = '{"matched_tags": [], "match_mode": "any", "confidence": 0.1, "reason": "No tags matched"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("Play some random music", ["Pop", "Rock"])
        
        assert not result.is_valid
        assert len(result.tags) == 0
    
    def test_parse_filters_invalid_tags(self):
        """Test that invalid tags (not in available_tags) are filtered out."""
        response = '{"matched_tags": ["Pop", "Non-existent Tag", "Rock"], "match_mode": "any", "confidence": 0.8}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("Give me some music", ["Pop", "Rock", "Classical"])
        
        assert "Pop" in result.tags
        assert "Rock" in result.tags
        assert "Non-existent Tag" not in result.tags
    
    def test_parse_case_insensitive_matching(self):
        """Test case-insensitive matching between LLM output and available tags."""
        response = '{"matched_tags": ["ROCK", "pop"], "match_mode": "any", "confidence": 0.8}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("Give me some music", ["Rock", "Pop", "Jazz"])
        
        assert len(result.tags) == 2
        # Should return tags with original casing
        assert "Rock" in result.tags or "Pop" in result.tags
    
    def test_parse_handles_json_with_code_fences(self):
        """Test handling of JSON wrapped in markdown code blocks."""
        response = '''```json
{"matched_tags": ["Pop"], "match_mode": "any", "confidence": 0.8}
```'''
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("Listen to some pop music", ["Pop", "Rock"])
        
        assert result.is_valid
        assert "Pop" in result.tags
    
    def test_parse_handles_empty_instruction(self):
        """Test handling of empty user instructions."""
        client = _FakeClient('{"matched_tags": []}')
        parser = TagQueryParser(client)
        
        result = parser.parse("", ["Pop", "Rock"])
        
        assert not result.is_valid
    
    def test_parse_handles_empty_available_tags(self):
        """Test handling of empty available tags list."""
        client = _FakeClient('{"matched_tags": []}')
        parser = TagQueryParser(client)
        
        result = parser.parse("Listen to music", [])
        
        assert not result.is_valid
        assert "No available tags" in result.reason
    
    def test_parse_handles_invalid_json(self):
        """Test handling of invalid JSON responses from LLM."""
        client = _FakeClient('not a json')
        parser = TagQueryParser(client)
        
        result = parser.parse("Listen to music", ["Pop"])
        
        assert not result.is_valid
        assert "Parsing failed" in result.reason or "non-JSON" in result.reason


class TestMultilingualTagQuery:
    """Tests for multilingual tag query parsing."""
    
    def test_chinese_query_matches_english_tag(self):
        """Test that Chinese query '摇滚' matches English tag 'Rock'."""
        response = '{"matched_tags": ["Rock"], "match_mode": "any", "confidence": 0.9, "reason": "User wants rock music"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("播放摇滚音乐", ["Rock", "Pop", "Jazz"])
        
        assert result.is_valid
        assert "Rock" in result.tags
        assert result.confidence >= 0.8
    
    def test_english_query_matches_chinese_tag(self):
        """Test that English query matches Chinese tag when available."""
        response = '{"matched_tags": ["流行"], "match_mode": "any", "confidence": 0.9, "reason": "User wants pop music"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("Play some pop music", ["流行", "摇滚", "古典"])
        
        assert result.is_valid
        assert "流行" in result.tags
    
    def test_mixed_language_query(self):
        """Test parsing query with mixed Chinese and English."""
        response = '{"matched_tags": ["Jay Chou", "Pop"], "match_mode": "all", "confidence": 0.85, "reason": "Mixed language query"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("我想听Jay Chou的流行歌", ["Jay Chou", "Pop", "Rock"])
        
        assert result.is_valid
        assert len(result.tags) >= 1
    
    def test_chinese_mood_query(self):
        """Test Chinese mood query matches English mood tags."""
        response = '{"matched_tags": ["Relaxing"], "match_mode": "any", "confidence": 0.88, "reason": "Relaxing music"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("我想听轻松的音乐", ["Relaxing", "Energetic", "Sad"])
        
        assert result.is_valid
        assert "Relaxing" in result.tags
    
    def test_bilingual_tags_available(self):
        """Test query when both language versions of tags are available."""
        response = '{"matched_tags": ["Rock", "摇滚"], "match_mode": "any", "confidence": 0.95, "reason": "Both versions matched"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("摇滚音乐", ["Rock", "摇滚", "Pop", "流行"])
        
        assert result.is_valid
        # Should match at least one
        assert len(result.tags) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
