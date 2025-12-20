"""
LLM 响应解析工具模块

提供 LLM 响应的共享解析功能：
- 移除代码块格式
- JSON 解析与自动修复
- Track ID 提取
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional, Set


logger = logging.getLogger(__name__)


class LLMParseError(RuntimeError):
    """LLM 响应解析错误"""
    pass


def strip_code_fences(text: str) -> str:
    """
    移除各种代码块格式
    
    处理格式:
    - ```json\\n...\\n```
    - ```\\n...\\n```
    - `...`
    - 前后空白
    
    Args:
        text: 原始文本
        
    Returns:
        移除代码块后的文本
    """
    t = text.strip()
    
    # 处理 ```...``` 格式（可能带语言标识）
    if t.startswith("```"):
        lines = t.splitlines()
        if len(lines) >= 2:
            # 找到结束的 ```
            end_idx = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip().startswith("```"):
                    end_idx = i
                    break
            # 移除首行和末行
            return "\n".join(lines[1:end_idx]).strip()
    
    # 处理单个反引号 `{...}`
    if t.startswith("`") and t.endswith("`") and not t.startswith("```"):
        return t[1:-1].strip()
    
    return t


def try_parse_json(
    text: str,
    raise_on_error: bool = True,
) -> Optional[dict]:
    """
    尝试解析 JSON，包含多种自动修复策略
    
    解析顺序:
    1. 直接解析
    2. 移除代码块后解析
    3. 正则提取 JSON 对象
    4. 修复常见格式问题（尾部逗号等）
    
    Args:
        text: 待解析文本
        raise_on_error: 解析失败时是否抛出异常
        
    Returns:
        解析后的字典，失败时返回 None 或抛出异常
        
    Raises:
        LLMParseError: 当 raise_on_error=True 且解析失败时
    """
    # 策略1: 直接解析
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 策略2: 移除代码块后解析
    raw = strip_code_fences(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    
    # 策略3: 正则提取 JSON 对象
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        extracted = match.group()
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            # 策略4: 修复尾部逗号问题
            fixed = re.sub(r',(\s*[}\]])', r'\1', extracted)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
    
    # 所有策略都失败
    logger.warning("LLM 返回无法解析的内容: %s", raw[:200])
    if raise_on_error:
        raise LLMParseError(f"LLM 返回非 JSON: {raw[:200]}")
    return None


def parse_track_ids_from_content(
    content: str,
    known_ids: Set[str],
    id_field: str = "track_ids",
) -> List[str]:
    """
    从 LLM 响应中提取 Track ID 列表
    
    Args:
        content: LLM 响应内容
        known_ids: 已知的有效 ID 集合
        id_field: JSON 中的 ID 字段名
        
    Returns:
        过滤后的有效 Track ID 列表
    """
    data = try_parse_json(content, raise_on_error=False)
    if not data:
        return []
    
    # 尝试多种字段名
    ids = data.get(id_field) or data.get("selected_ids") or []
    
    if not isinstance(ids, list):
        return []
    
    # 过滤无效 ID
    result = []
    for track_id in ids:
        if isinstance(track_id, str) and track_id in known_ids:
            result.append(track_id)
    
    return result


def parse_tags_from_content(
    content: str,
    known_ids: Set[str],
    tags_field: str = "tags",
    max_tag_length: int = 50,
) -> Dict[str, List[str]]:
    """
    从 LLM 响应中提取标签字典
    
    Args:
        content: LLM 响应内容
        known_ids: 已知的有效 Track ID 集合
        tags_field: JSON 中的标签字段名
        max_tag_length: 单个标签最大长度
        
    Returns:
        {track_id: [tag1, tag2, ...]} 字典
    """
    data = try_parse_json(content, raise_on_error=False)
    if not data:
        return {}
    
    tags_data = data.get(tags_field, {})
    if not isinstance(tags_data, dict):
        return {}
    
    result: Dict[str, List[str]] = {}
    for track_id, tags in tags_data.items():
        if track_id not in known_ids:
            continue
        if not isinstance(tags, list):
            continue
        
        # 过滤有效标签
        valid_tags = []
        for tag in tags:
            if isinstance(tag, str):
                tag = tag.strip()
                if tag and len(tag) <= max_tag_length:
                    valid_tags.append(tag)
        
        if valid_tags:
            result[track_id] = valid_tags
    
    return result
