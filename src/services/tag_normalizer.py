"""
Tag Normalizer Module

Provides tag alias resolution and multilingual tag normalization.
This enables cross-language tag matching without database changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# Common tag mappings (built-in, no DB required)
# Key is canonical (lowercase English), value is set of aliases
BUILTIN_ALIASES: Dict[str, Set[str]] = {
    # Genre mappings
    "rock": {"摇滚", "ロック", "락"},
    "pop": {"流行", "ポップ", "팝"},
    "classical": {"古典", "クラシック", "클래식"},
    "electronic": {"电子", "エレクトロニック", "일렉트로닉"},
    "jazz": {"爵士", "ジャズ", "재즈"},
    "hip-hop": {"嘻哈", "ヒップホップ", "힙합"},
    "r&b": {"节奏蓝调", "アールアンドビー", "알앤비"},
    "folk": {"民谣", "フォーク", "포크"},
    "country": {"乡村", "カントリー", "컨트리"},
    "blues": {"蓝调", "ブルース", "블루스"},
    "metal": {"金属", "メタル", "메탈"},
    "punk": {"朋克", "パンク", "펑크"},
    "indie": {"独立", "インディー", "인디"},
    "soul": {"灵魂乐", "ソウル", "소울"},
    "reggae": {"雷鬼", "レゲエ", "레게"},
    
    # Mood mappings
    "relaxing": {"轻松", "放松", "リラックス", "편안한"},
    "energetic": {"活力", "劲爆", "エネルギッシュ", "에너지"},
    "sad": {"悲伤", "忧伤", "悲しい", "슬픈"},
    "happy": {"欢快", "快乐", "楽しい", "행복한"},
    "romantic": {"浪漫", "ロマンチック", "로맨틱"},
    "melancholic": {"忧郁", "メランコリック", "우울한"},
    "peaceful": {"平静", "安静", "穏やか", "평화로운"},
    "exciting": {"激动", "兴奋", "エキサイティング", "흥분"},
    "chill": {"慵懒", "チル", "칠"},
    
    # Language mappings
    "chinese": {"华语", "中文", "國語", "粤语", "普通话"},
    "english": {"英文", "英语"},
    "japanese": {"日语", "日本語", "日文"},
    "korean": {"韩语", "韩文", "한국어"},
    "cantonese": {"粤语", "广东话"},
    "mandarin": {"国语", "普通话", "华语"},
    
    # Era mappings
    "80s": {"八十年代", "80年代"},
    "90s": {"九十年代", "90年代"},
    "2000s": {"零零年代", "00年代"},
    "classic": {"经典", "クラシック"},
    "modern": {"现代", "モダン"},
    "retro": {"复古", "レトロ"},
    
    # Other characteristics
    "instrumental": {"纯音乐", "器乐", "インストゥルメンタル"},
    "live": {"现场", "ライブ"},
    "acoustic": {"原声", "木吉他", "アコースティック"},
    "cover": {"翻唱", "カバー"},
}


@dataclass
class TagNormalizationResult:
    """Result of tag normalization."""
    original: str
    normalized: str
    aliases: List[str]
    is_alias: bool


class TagNormalizer:
    """
    Tag Normalizer
    
    Resolves tag aliases and provides multilingual tag matching.
    Uses only built-in mappings without database dependency.
    
    Example:
        normalizer = TagNormalizer()
        
        # Normalize Chinese to canonical English
        result = normalizer.normalize("摇滚")
        # -> TagNormalizationResult(original="摇滚", normalized="rock", ...)
        
        # Find matching tags across languages
        matches = normalizer.find_matching_tags(
            query_tags=["摇滚", "流行"],
            available_tags=["Rock", "Pop", "Jazz"],
        )
        # -> ["Rock", "Pop"]
    """
    
    def __init__(self) -> None:
        """Initialize the normalizer with built-in alias mappings."""
        self._alias_cache: Dict[str, str] = {}
        self._reverse_cache: Dict[str, Set[str]] = {}
        self._build_cache()
    
    def _build_cache(self) -> None:
        """Build alias lookup caches from builtin mappings."""
        for canonical, aliases in BUILTIN_ALIASES.items():
            # canonical -> canonical (self-reference)
            self._alias_cache[canonical.lower()] = canonical
            self._reverse_cache[canonical] = set(aliases)
            
            # alias -> canonical
            for alias in aliases:
                self._alias_cache[alias.lower()] = canonical
    
    def normalize(self, tag: str) -> TagNormalizationResult:
        """
        Normalize a tag to its canonical form.
        
        Args:
            tag: Tag to normalize
            
        Returns:
            TagNormalizationResult with canonical form and aliases
        """
        tag_stripped = tag.strip()
        tag_lower = tag_stripped.lower()
        
        if tag_lower in self._alias_cache:
            canonical = self._alias_cache[tag_lower]
            aliases = list(self._reverse_cache.get(canonical, set()))
            return TagNormalizationResult(
                original=tag,
                normalized=canonical,
                aliases=aliases,
                is_alias=(tag_lower != canonical),
            )
        
        return TagNormalizationResult(
            original=tag,
            normalized=tag_stripped,
            aliases=[],
            is_alias=False,
        )
    
    def find_matching_tags(
        self,
        query_tags: List[str],
        available_tags: List[str],
    ) -> List[str]:
        """
        Find matching tags considering aliases across languages.
        
        Args:
            query_tags: Tags to search for (may be in any language)
            available_tags: List of available tags to match against
            
        Returns:
            List of matching available tags
        """
        matches: Set[str] = set()
        
        # Build lowercase lookup for available tags
        available_lower = {t.strip().lower(): t for t in available_tags}
        
        for query in query_tags:
            query_stripped = query.strip()
            query_lower = query_stripped.lower()
            
            # Direct match (case-insensitive)
            if query_lower in available_lower:
                matches.add(available_lower[query_lower])
                continue
            
            # Normalize and try canonical form
            result = self.normalize(query)
            
            # Try canonical form
            if result.normalized.lower() in available_lower:
                matches.add(available_lower[result.normalized.lower()])
                continue
            
            # Try all aliases
            for alias in result.aliases:
                alias_lower = alias.lower()
                if alias_lower in available_lower:
                    matches.add(available_lower[alias_lower])
                    # Don't break - there might be multiple matching aliases
        
        return list(matches)
    
    def get_all_aliases(self, tag: str) -> List[str]:
        """
        Get all aliases for a tag including the canonical form.
        
        Args:
            tag: Tag to get aliases for
            
        Returns:
            List of all forms of the tag (canonical + aliases)
        """
        result = self.normalize(tag)
        all_forms = [result.normalized] + result.aliases
        return all_forms
    
    def are_equivalent(self, tag1: str, tag2: str) -> bool:
        """
        Check if two tags are equivalent (same canonical form).
        
        Args:
            tag1: First tag
            tag2: Second tag
            
        Returns:
            True if tags have the same canonical form
        """
        result1 = self.normalize(tag1)
        result2 = self.normalize(tag2)
        return result1.normalized.lower() == result2.normalized.lower()
