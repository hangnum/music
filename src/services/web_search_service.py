"""
网络搜索服务

使用 DuckDuckGo 提供免费的网络搜索功能，辅助 LLM 打标签。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    body: str
    url: str


class WebSearchService:
    """
    网络搜索服务
    
    使用 DuckDuckGo 搜索引擎获取音乐相关信息，
    用于增强 LLM 标签标注的准确性。
    
    使用示例:
        service = WebSearchService()
        context = service.get_music_context("周杰伦", "七里香", "七里香")
        # -> "风格: R&B/流行 | 特点: 中国风元素 | ..."
    """
    
    # 高质量音乐信息站点
    TRUSTED_SITES = [
        "music.163.com",
        "baike.baidu.com", 
        "douban.com",
        "qq.com",
    ]
    
    # 过滤无关内容的关键词
    NOISE_PATTERNS = [
        r"登录|注册|下载|安装|广告",
        r"404|页面不存在|访问出错",
        r"点击.*查看|立即.*体验",
    ]
    
    def __init__(self, timeout: float = 10.0):
        """
        初始化搜索服务
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self._timeout = timeout
        self._ddgs = None
        self._noise_re = re.compile("|".join(self.NOISE_PATTERNS))
    
    def _get_ddgs(self):
        """懒加载 DDGS 客户端"""
        if self._ddgs is None:
            try:
                from ddgs import DDGS
                self._ddgs = DDGS(timeout=self._timeout)
            except ImportError:
                logger.warning("ddgs 未安装，请运行: pip install ddgs")
                return None
        return self._ddgs
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除噪音内容"""
        if not text:
            return ""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        # 检查是否包含噪音
        if self._noise_re.search(text):
            return ""
        return text
    
    def _is_relevant(self, body: str, keywords: List[str]) -> bool:
        """检查结果是否与关键词相关"""
        if not body or not keywords:
            return True  # 无关键词时不过滤
        body_lower = body.lower()
        return any(kw.lower() in body_lower for kw in keywords if kw)
    
    def _deduplicate(self, texts: List[str]) -> List[str]:
        """去重，保留顺序"""
        seen: Set[str] = set()
        result = []
        for t in texts:
            # 使用前50字符作为去重key
            key = t[:50].lower() if len(t) >= 50 else t.lower()
            if key not in seen:
                seen.add(key)
                result.append(t)
        return result
    
    def search_music_info(
        self,
        artist: str,
        title: str,
        max_results: int = 5,
    ) -> List[str]:
        """
        搜索歌曲相关信息（改进版）
        
        使用多查询策略，优先从高质量站点获取结果。
        
        Args:
            artist: 艺术家名称
            title: 歌曲标题
            max_results: 最大返回结果数
            
        Returns:
            搜索结果摘要列表（已过滤和去重）
        """
        if not artist and not title:
            return []
        
        all_results = []
        keywords = [k for k in [artist, title] if k]
        
        # 策略1: 精确搜索（带引号）
        if artist and title:
            query = f'"{artist}" "{title}" 音乐风格'
            results = self._do_search(query, max_results=3)
            all_results.extend(results)
        
        # 策略2: 通用搜索
        if len(all_results) < max_results:
            query_parts = keywords + ["歌曲", "风格"]
            query = " ".join(query_parts)
            results = self._do_search(query, max_results=3)
            all_results.extend(results)
        
        # 过滤和去重
        filtered = [r for r in all_results if self._is_relevant(r, keywords)]
        return self._deduplicate(filtered)[:max_results]
    
    def search_artist_info(
        self,
        artist: str,
        max_results: int = 3,
    ) -> List[str]:
        """
        搜索艺术家信息
        
        Args:
            artist: 艺术家名称
            max_results: 最大返回结果数
            
        Returns:
            搜索结果摘要列表
        """
        if not artist:
            return []
        
        # 使用更精确的查询
        query = f'"{artist}" 歌手 音乐风格 代表作'
        results = self._do_search(query, max_results=max_results + 2)
        
        # 过滤包含艺术家名的结果
        filtered = [r for r in results if artist.lower() in r.lower()]
        return filtered[:max_results] if filtered else results[:max_results]
    
    def search_album_info(
        self,
        artist: str,
        album: str,
        max_results: int = 3,
    ) -> List[str]:
        """
        搜索专辑信息
        
        Args:
            artist: 艺术家名称
            album: 专辑名称
            max_results: 最大返回结果数
            
        Returns:
            搜索结果摘要列表
        """
        if not album:
            return []
        
        # 精确搜索专辑
        if artist:
            query = f'"{artist}" "{album}" 专辑 风格'
        else:
            query = f'"{album}" 专辑 音乐风格'
        
        results = self._do_search(query, max_results=max_results + 2)
        
        # 过滤包含专辑名的结果
        filtered = [r for r in results if album.lower() in r.lower()]
        return filtered[:max_results] if filtered else results[:max_results]
    
    def _do_search(
        self,
        query: str,
        max_results: int,
    ) -> List[str]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            结果摘要列表
        """
        ddgs = self._get_ddgs()
        if ddgs is None:
            return []
        
        try:
            results = list(ddgs.text(
                query,
                max_results=max_results,
                region="cn-zh",
            ))
            
            summaries = []
            for r in results:
                body = self._clean_text(r.get("body", ""))
                if not body:
                    continue
                
                # 限制每条结果的长度，确保在句子边界截断
                if len(body) > 150:
                    # 尝试在句号处截断
                    cut_pos = body.rfind("。", 0, 150)
                    if cut_pos > 50:
                        body = body[:cut_pos + 1]
                    else:
                        body = body[:150] + "…"
                
                summaries.append(body)
            
            logger.debug("搜索 '%s' 返回 %d 条有效结果", query, len(summaries))
            return summaries
            
        except Exception as e:
            logger.warning("搜索失败: %s", e)
            return []
    
    def get_music_context(
        self,
        artist: Optional[str],
        title: Optional[str],
        album: Optional[str],
        max_total_chars: int = 500,
    ) -> str:
        """
        获取综合的音乐上下文信息（改进版）
        
        生成结构化的上下文，便于 LLM 解析。
        
        Args:
            artist: 艺术家名称
            title: 歌曲标题
            album: 专辑名称
            max_total_chars: 最大总字符数
            
        Returns:
            结构化的上下文字符串
        """
        context_parts = []
        chars_used = 0
        
        # 1. 优先搜索歌曲信息
        if title:
            song_info = self.search_music_info(artist or "", title, max_results=2)
            for info in song_info:
                if chars_used + len(info) < max_total_chars * 0.6:
                    context_parts.append(f"[歌曲] {info}")
                    chars_used += len(info)
        
        # 2. 补充艺术家信息
        if artist and chars_used < max_total_chars * 0.8:
            artist_info = self.search_artist_info(artist, max_results=1)
            for info in artist_info:
                if chars_used + len(info) < max_total_chars * 0.9:
                    context_parts.append(f"[艺术家] {info}")
                    chars_used += len(info)
        
        # 3. 补充专辑信息（如果还有空间）
        if album and chars_used < max_total_chars * 0.9:
            album_info = self.search_album_info(artist or "", album, max_results=1)
            for info in album_info:
                if chars_used + len(info) < max_total_chars:
                    context_parts.append(f"[专辑] {info}")
                    chars_used += len(info)
        
        if not context_parts:
            return ""
        
        # 使用换行分隔，更易于 LLM 解析
        context = "\n".join(context_parts)
        
        # 最终长度控制
        if len(context) > max_total_chars:
            context = context[:max_total_chars - 3] + "..."
        
        return context
