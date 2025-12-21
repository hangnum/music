"""
Tag Normalizer Tests

Tests for multilingual tag normalization and alias resolution.
"""

import pytest

from services.tag_normalizer import TagNormalizer, BUILTIN_ALIASES, TagNormalizationResult


class TestBuiltinAliases:
    """Tests for the built-in alias mappings."""
    
    def test_genre_mappings_exist(self):
        """Verify common genre mappings are defined."""
        assert "rock" in BUILTIN_ALIASES
        assert "pop" in BUILTIN_ALIASES
        assert "jazz" in BUILTIN_ALIASES
        assert "classical" in BUILTIN_ALIASES
    
    def test_mood_mappings_exist(self):
        """Verify common mood mappings are defined."""
        assert "relaxing" in BUILTIN_ALIASES
        assert "energetic" in BUILTIN_ALIASES
        assert "sad" in BUILTIN_ALIASES
        assert "happy" in BUILTIN_ALIASES
    
    def test_language_mappings_exist(self):
        """Verify language mappings are defined."""
        assert "chinese" in BUILTIN_ALIASES
        assert "english" in BUILTIN_ALIASES
        assert "japanese" in BUILTIN_ALIASES
        assert "korean" in BUILTIN_ALIASES


class TestTagNormalizer:
    """Tests for TagNormalizer."""
    
    def test_normalize_english_tag(self):
        """Test normalizing a canonical English tag."""
        normalizer = TagNormalizer()
        result = normalizer.normalize("rock")
        
        assert result.normalized == "rock"
        assert result.is_alias is False
        assert "摇滚" in result.aliases
    
    def test_normalize_chinese_alias(self):
        """Test normalizing a Chinese alias to canonical form."""
        normalizer = TagNormalizer()
        result = normalizer.normalize("摇滚")
        
        assert result.normalized == "rock"
        assert result.is_alias is True
    
    def test_normalize_case_insensitive(self):
        """Test case-insensitive normalization."""
        normalizer = TagNormalizer()
        
        result1 = normalizer.normalize("ROCK")
        result2 = normalizer.normalize("Rock")
        result3 = normalizer.normalize("rock")
        
        assert result1.normalized == result2.normalized == result3.normalized == "rock"
    
    def test_normalize_unknown_tag(self):
        """Test normalizing an unknown tag returns original."""
        normalizer = TagNormalizer()
        result = normalizer.normalize("Unknown Genre XYZ")
        
        assert result.normalized == "Unknown Genre XYZ"
        assert result.is_alias is False
        assert result.aliases == []
    
    def test_normalize_preserves_original(self):
        """Test that original tag is preserved."""
        normalizer = TagNormalizer()
        result = normalizer.normalize("  摇滚  ")
        
        assert result.original == "  摇滚  "
        assert result.normalized == "rock"
    
    def test_find_matching_tags_direct_match(self):
        """Test direct matching when tag exists."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["Rock"],
            available_tags=["Rock", "Pop", "Jazz"],
        )
        
        assert "Rock" in matches
    
    def test_find_matching_tags_cross_language_chinese_to_english(self):
        """Test matching Chinese query to English tag."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["摇滚", "流行"],
            available_tags=["Rock", "Pop", "Jazz"],
        )
        
        assert "Rock" in matches
        assert "Pop" in matches
        assert len(matches) == 2
    
    def test_find_matching_tags_cross_language_english_to_chinese(self):
        """Test matching English query to Chinese tag."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["rock", "pop"],
            available_tags=["摇滚", "流行", "爵士"],
        )
        
        assert "摇滚" in matches
        assert "流行" in matches
    
    def test_find_matching_tags_case_insensitive(self):
        """Test case-insensitive matching."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["ROCK"],
            available_tags=["rock", "pop"],
        )
        
        assert "rock" in matches
    
    def test_find_matching_tags_no_duplicates(self):
        """Test that duplicate matches are not returned."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["rock", "Rock", "ROCK", "摇滚"],
            available_tags=["Rock"],
        )
        
        assert len(matches) == 1
        assert "Rock" in matches
    
    def test_find_matching_tags_empty_query(self):
        """Test empty query returns empty list."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=[],
            available_tags=["Rock", "Pop"],
        )
        
        assert matches == []
    
    def test_find_matching_tags_no_match(self):
        """Test query with no matching tags."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["Unknown"],
            available_tags=["Rock", "Pop"],
        )
        
        assert matches == []
    
    def test_get_all_aliases(self):
        """Test getting all aliases for a tag."""
        normalizer = TagNormalizer()
        
        aliases = normalizer.get_all_aliases("rock")
        
        assert "rock" in aliases
        assert "摇滚" in aliases
    
    def test_get_all_aliases_for_alias(self):
        """Test getting aliases starting from an alias."""
        normalizer = TagNormalizer()
        
        aliases = normalizer.get_all_aliases("摇滚")
        
        assert "rock" in aliases
        assert "摇滚" in aliases
    
    def test_are_equivalent_same_language(self):
        """Test equivalence check for same language."""
        normalizer = TagNormalizer()
        
        assert normalizer.are_equivalent("rock", "Rock") is True
        assert normalizer.are_equivalent("Rock", "ROCK") is True
    
    def test_are_equivalent_cross_language(self):
        """Test equivalence check across languages."""
        normalizer = TagNormalizer()
        
        assert normalizer.are_equivalent("rock", "摇滚") is True
        assert normalizer.are_equivalent("pop", "流行") is True
    
    def test_are_equivalent_different_tags(self):
        """Test non-equivalent tags."""
        normalizer = TagNormalizer()
        
        assert normalizer.are_equivalent("rock", "pop") is False
        assert normalizer.are_equivalent("摇滚", "流行") is False


class TestMultilingualMoodMatching:
    """Tests for mood tag matching across languages."""
    
    def test_relaxing_mood_matching(self):
        """Test relaxing mood matches across languages."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["轻松"],
            available_tags=["Relaxing", "Energetic"],
        )
        
        assert "Relaxing" in matches
    
    def test_energetic_mood_matching(self):
        """Test energetic mood matches across languages."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["活力"],
            available_tags=["Relaxing", "Energetic"],
        )
        
        assert "Energetic" in matches


class TestMultilingualLanguageMatching:
    """Tests for language tag matching across languages."""
    
    def test_chinese_language_tag_matching(self):
        """Test Chinese language tag matches."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["华语", "中文"],
            available_tags=["Chinese", "English", "Japanese"],
        )
        
        assert "Chinese" in matches
    
    def test_english_language_tag_matching(self):
        """Test English language tag matches."""
        normalizer = TagNormalizer()
        
        matches = normalizer.find_matching_tags(
            query_tags=["英文"],
            available_tags=["Chinese", "English", "Japanese"],
        )
        
        assert "English" in matches


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
