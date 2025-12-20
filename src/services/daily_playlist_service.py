"""
每日歌单服务

根据用户输入的标签生成今日歌单，支持三层筛选策略:
1. 直接标签匹配
2. LLM 语义扩展
3. 随机补充
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.library_service import LibraryService
    from services.tag_service import TagService

from models.track import Track

logger = logging.getLogger(__name__)


@dataclass
class DailyPlaylistResult:
    """每日歌单生成结果"""
    
    tracks: List[Track] = field(default_factory=list)
    matched_by_tags: int = 0          # 直接标签匹配的曲目数
    matched_by_semantic: int = 0      # 语义扩展匹配的曲目数
    filled_random: int = 0            # 随机补充的曲目数
    expanded_tags: List[str] = field(default_factory=list)  # LLM 扩展的标签列表
    input_tags: List[str] = field(default_factory=list)     # 用户输入的原始标签
    
    @property
    def total(self) -> int:
        """返回歌单中的曲目总数"""
        return len(self.tracks)
    
    @property
    def summary(self) -> str:
        """返回生成结果摘要"""
        parts = []
        if self.matched_by_tags > 0:
            parts.append(f"标签匹配 {self.matched_by_tags} 首")
        if self.matched_by_semantic > 0:
            parts.append(f"语义扩展 {self.matched_by_semantic} 首")
        if self.filled_random > 0:
            parts.append(f"随机补充 {self.filled_random} 首")
        return " / ".join(parts) if parts else "无匹配结果"


class DailyPlaylistService:
    """
    每日歌单生成服务
    
    使用三层筛选策略生成今日歌单:
    1. 直接使用用户提供的标签筛选曲目
    2. 如果不够，调用 LLM 扩展语义相近的标签
    3. 如果仍不够，随机补充音乐库中的曲目
    
    使用示例:
        service = DailyPlaylistService(tag_service, library_service, llm_provider)
        result = service.generate(["流行", "轻松"], limit=50)
        print(f"生成了 {result.total} 首歌: {result.summary}")
    """
    
    def __init__(
        self,
        tag_service: "TagService",
        library_service: "LibraryService",
        llm_provider: Optional["LLMProvider"] = None,
    ):
        """
        初始化每日歌单服务
        
        Args:
            tag_service: 标签服务实例
            library_service: 媒体库服务实例
            llm_provider: LLM 提供商实例（可选，用于语义扩展）
        """
        self._tag_service = tag_service
        self._library_service = library_service
        self._llm_provider = llm_provider
    
    def generate(
        self,
        input_tags: List[str],
        limit: int = 50,
        shuffle: bool = True,
    ) -> DailyPlaylistResult:
        """
        生成每日歌单
        
        Args:
            input_tags: 用户输入的标签列表
            limit: 目标曲目数量（默认 50）
            shuffle: 是否打乱顺序（默认 True）
            
        Returns:
            DailyPlaylistResult 包含生成的曲目和统计信息
        """
        result = DailyPlaylistResult(input_tags=list(input_tags))
        collected: List[Track] = []
        collected_ids: set[str] = set()
        
        # 清理输入标签
        input_tags = [t.strip() for t in input_tags if t.strip()]
        
        if not input_tags:
            logger.warning("没有提供有效的标签，将直接使用随机补充")
        else:
            # Step 1: 直接标签匹配
            logger.info("Step 1: 直接标签匹配，标签: %s", input_tags)
            track_ids = self._tag_service.get_tracks_by_tags(
                input_tags, match_mode="any", limit=limit
            )
            
            if track_ids:
                tracks = self._library_service.get_tracks_by_ids(track_ids)
                for track in tracks:
                    if track.id not in collected_ids:
                        collected.append(track)
                        collected_ids.add(track.id)
                result.matched_by_tags = len(collected)
                logger.info("直接标签匹配找到 %d 首曲目", result.matched_by_tags)
            
            # Step 2: LLM 语义扩展
            if len(collected) < limit and self._llm_provider:
                logger.info("Step 2: LLM 语义扩展")
                remaining = limit - len(collected)
                expanded_tags = self._expand_tags_with_llm(input_tags)
                result.expanded_tags = expanded_tags
                
                # 过滤掉已经使用的标签
                new_tags = [t for t in expanded_tags if t.lower() not in 
                           {tag.lower() for tag in input_tags}]
                
                if new_tags:
                    logger.info("LLM 扩展了 %d 个新标签: %s", len(new_tags), new_tags)
                    more_ids = self._tag_service.get_tracks_by_tags(
                        new_tags, match_mode="any", limit=remaining * 2
                    )
                    
                    if more_ids:
                        more_tracks = self._library_service.get_tracks_by_ids(more_ids)
                        semantic_count = 0
                        for track in more_tracks:
                            if track.id not in collected_ids:
                                collected.append(track)
                                collected_ids.add(track.id)
                                semantic_count += 1
                                if len(collected) >= limit:
                                    break
                        result.matched_by_semantic = semantic_count
                        logger.info("语义扩展找到 %d 首新曲目", semantic_count)
                else:
                    logger.info("LLM 没有扩展出新标签")
        
        # Step 3: 随机补充
        if len(collected) < limit:
            remaining = limit - len(collected)
            logger.info("Step 3: 随机补充 %d 首曲目", remaining)
            
            # 获取更多曲目以便去重
            random_tracks = self._library_service.query_tracks(
                limit=remaining * 3, shuffle=True
            )
            
            random_count = 0
            for track in random_tracks:
                if track.id not in collected_ids:
                    collected.append(track)
                    collected_ids.add(track.id)
                    random_count += 1
                    if len(collected) >= limit:
                        break
            
            result.filled_random = random_count
            logger.info("随机补充了 %d 首曲目", random_count)
        
        # 打乱顺序
        if shuffle and len(collected) > 1:
            random.shuffle(collected)
        
        result.tracks = collected
        logger.info("每日歌单生成完成: %s", result.summary)
        
        return result
    
    def _expand_tags_with_llm(self, input_tags: List[str]) -> List[str]:
        """
        使用 LLM 扩展语义相近的标签
        
        Args:
            input_tags: 用户输入的标签列表
            
        Returns:
            扩展后的标签列表（包含原始标签和语义相近的标签）
        """
        if not self._llm_provider:
            return []
        
        # 获取所有可用标签
        all_tags = self._tag_service.get_all_tag_names()
        if not all_tags:
            logger.debug("没有可用标签供扩展")
            return []
        
        # 限制发送给 LLM 的标签数量
        max_tags = 500
        tags_sample = all_tags[:max_tags]
        
        messages = self._build_expand_messages(input_tags, tags_sample)
        
        try:
            content = self._llm_provider.chat_completions(messages)
            return self._parse_expand_response(content, set(all_tags))
        except Exception as e:
            logger.warning("LLM 标签扩展失败: %s", e)
            return []
    
    def _build_expand_messages(
        self,
        input_tags: List[str],
        available_tags: List[str],
    ) -> List[Dict[str, str]]:
        """构建 LLM 标签扩展请求消息"""
        payload = {
            "task": "expand_music_tags",
            "user_tags": input_tags,
            "available_tags": available_tags,
            "note": f"共有 {len(available_tags)} 个可用标签",
            "response_schema": {
                "expanded_tags": ["标签1", "标签2", "..."],
                "reason": "简短说明扩展理由",
            },
            "rules": [
                "只输出 JSON（不要 markdown，不要代码块）。",
                "expanded_tags 必须来自 available_tags 中的标签（不区分大小写）。",
                "找出与 user_tags 语义相近、风格相似、或常一起出现的标签。",
                "返回 10-20 个最相关的标签。",
                "可以包含 user_tags 中的原始标签。",
            ],
        }
        
        system = (
            "你是音乐标签扩展助手。根据用户提供的标签，"
            "从可用标签中找出语义相近或风格相似的标签，"
            "帮助用户发现更多可能喜欢的音乐。"
            "严格按 schema 输出 JSON，且不要输出除 JSON 之外的任何内容。"
        )
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def _parse_expand_response(
        self,
        content: str,
        available_tags_set: set,
    ) -> List[str]:
        """解析 LLM 扩展响应"""
        raw = self._strip_code_fences(content).strip()
        
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning("LLM 返回非 JSON: %s", raw[:200])
            return []
        
        # 提取扩展的标签
        expanded = data.get("expanded_tags", [])
        if not isinstance(expanded, list):
            expanded = []
        
        # 不区分大小写匹配
        available_lower = {t.lower(): t for t in available_tags_set}
        valid_tags = []
        for tag in expanded:
            if isinstance(tag, str):
                tag_lower = tag.strip().lower()
                if tag_lower in available_lower:
                    valid_tags.append(available_lower[tag_lower])
        
        return valid_tags
    
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """移除代码块标记"""
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                return "\n".join(lines[1:-1])
        return t
