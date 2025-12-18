"""
标签查询解析器

将用户的自然语言指令解析为标签查询条件。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.tag_service import TagService

logger = logging.getLogger(__name__)


@dataclass
class TagQuery:
    """标签查询结果"""
    tags: List[str] = field(default_factory=list)
    match_mode: str = "any"  # "any" | "all"
    confidence: float = 0.0  # 0.0 - 1.0
    reason: str = ""
    
    @property
    def is_valid(self) -> bool:
        """查询是否有效（有匹配的标签）"""
        return len(self.tags) > 0


class TagQueryParser:
    """
    将自然语言解析为标签查询条件
    
    示例:
        parser = TagQueryParser(client, tag_service)
        
        query = parser.parse("我想听周杰伦的歌", available_tags)
        # -> TagQuery(tags=["周杰伦"], match_mode="any", confidence=0.9)
        
        query = parser.parse("放松的古典音乐", available_tags)
        # -> TagQuery(tags=["古典", "放松"], match_mode="all", confidence=0.8)
    """
    
    def __init__(
        self,
        client: "LLMProvider",
        tag_service: Optional["TagService"] = None,
    ):
        """
        初始化解析器
        
        Args:
            client: LLM 提供商
            tag_service: 标签服务（可选，用于获取可用标签）
        """
        self._client = client
        self._tag_service = tag_service
    
    def parse(
        self,
        instruction: str,
        available_tags: Optional[List[str]] = None,
    ) -> TagQuery:
        """
        解析自然语言指令为标签查询
        
        Args:
            instruction: 用户的自然语言指令
            available_tags: 可用的标签列表（为 None 则从 TagService 获取）
            
        Returns:
            TagQuery 对象
        """
        if not instruction.strip():
            return TagQuery()
        
        # 获取可用标签
        if available_tags is None:
            if self._tag_service:
                available_tags = self._tag_service.get_all_tag_names()
            else:
                available_tags = []
        
        if not available_tags:
            logger.debug("没有可用标签，返回空查询")
            return TagQuery(reason="没有可用标签")
        
        messages = self._build_parse_messages(instruction, available_tags)
        
        try:
            content = self._client.chat_completions(messages)
            return self._parse_response(content, set(available_tags))
        except Exception as e:
            logger.warning("解析标签查询失败: %s", e)
            return TagQuery(reason=f"解析失败: {e}")
    
    def _build_parse_messages(
        self,
        instruction: str,
        available_tags: List[str],
    ) -> List[Dict[str, str]]:
        """构建解析请求消息"""
        # 限制可用标签数量，避免 token 过多
        max_tags = 500
        tags_sample = available_tags[:max_tags]
        
        payload = {
            "task": "parse_music_query",
            "instruction": instruction,
            "available_tags": tags_sample,
            "note": f"共有 {len(available_tags)} 个可用标签" + (
                f"，这里展示前 {max_tags} 个" if len(available_tags) > max_tags else ""
            ),
            "response_schema": {
                "matched_tags": ["标签1", "标签2"],
                "match_mode": "any|all",
                "confidence": 0.8,
                "reason": "简短说明",
            },
            "rules": [
                "只输出 JSON（不要 markdown，不要代码块）。",
                "matched_tags 必须来自 available_tags 中的标签（不区分大小写）。",
                "如果用户指令明确要求同时满足多个条件，使用 match_mode='all'。",
                "如果用户指令表示'或'的关系，使用 match_mode='any'。",
                "confidence 表示匹配的置信度（0.0-1.0）。",
                "如果无法匹配任何标签，返回空的 matched_tags。",
            ],
        }
        
        system = (
            "你是音乐查询解析助手。根据用户的自然语言指令，"
            "从可用标签中找出最相关的标签。"
            "严格按 schema 输出 JSON，且不要输出除 JSON 之外的任何内容。"
        )
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def _parse_response(
        self,
        content: str,
        available_tags_set: set,
    ) -> TagQuery:
        """解析 LLM 响应"""
        raw = self._strip_code_fences(content).strip()
        
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning("LLM 返回非 JSON: %s", raw[:200])
            return TagQuery(reason=f"LLM 返回非 JSON: {raw[:200]}")
        
        # 提取匹配的标签
        matched = data.get("matched_tags", [])
        if not isinstance(matched, list):
            matched = []
        
        # 不区分大小写匹配
        available_lower = {t.lower(): t for t in available_tags_set}
        valid_tags = []
        for tag in matched:
            if isinstance(tag, str):
                tag_lower = tag.strip().lower()
                if tag_lower in available_lower:
                    valid_tags.append(available_lower[tag_lower])
        
        # 提取匹配模式
        match_mode = data.get("match_mode", "any")
        if match_mode not in {"any", "all"}:
            match_mode = "any"
        
        # 提取置信度
        confidence = data.get("confidence", 0.0)
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.0
        
        reason = data.get("reason", "")
        if not isinstance(reason, str):
            reason = ""
        
        return TagQuery(
            tags=valid_tags,
            match_mode=match_mode,
            confidence=confidence,
            reason=reason,
        )
    
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """移除代码块标记"""
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                return "\n".join(lines[1:-1])
        return t
