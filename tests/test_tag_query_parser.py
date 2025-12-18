"""
标签查询解析器测试
"""

import pytest

from services.tag_query_parser import TagQueryParser, TagQuery


class _FakeClient:
    """模拟 LLM 客户端"""
    def __init__(self, response: str):
        self._response = response
    
    def chat_completions(self, _messages):
        return self._response


class TestTagQuery:
    """TagQuery 数据类测试"""
    
    def test_is_valid_with_tags(self):
        """测试有标签时 is_valid 为 True"""
        query = TagQuery(tags=["Pop", "Rock"])
        assert query.is_valid is True
    
    def test_is_valid_without_tags(self):
        """测试无标签时 is_valid 为 False"""
        query = TagQuery(tags=[])
        assert query.is_valid is False
    
    def test_default_values(self):
        """测试默认值"""
        query = TagQuery()
        assert query.tags == []
        assert query.match_mode == "any"
        assert query.confidence == 0.0
        assert query.reason == ""


class TestTagQueryParser:
    """TagQueryParser 测试"""
    
    def test_parse_artist_query(self):
        """测试解析艺术家查询"""
        response = '{"matched_tags": ["周杰伦"], "match_mode": "any", "confidence": 0.9, "reason": "用户想听周杰伦的歌"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("我想听周杰伦的歌", ["周杰伦", "林俊杰", "流行"])
        
        assert result.is_valid
        assert "周杰伦" in result.tags
        assert result.match_mode == "any"
        assert result.confidence >= 0.8
    
    def test_parse_genre_query(self):
        """测试解析流派查询"""
        response = '{"matched_tags": ["摇滚", "激昂"], "match_mode": "any", "confidence": 0.85, "reason": "用户想听摇滚音乐"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("来点摇滚音乐", ["流行", "摇滚", "古典", "激昂", "放松"])
        
        assert result.is_valid
        assert "摇滚" in result.tags
    
    def test_parse_mood_query(self):
        """测试解析情绪查询"""
        response = '{"matched_tags": ["放松", "轻音乐"], "match_mode": "all", "confidence": 0.75, "reason": "用户想听放松的音乐"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("放松一下", ["激昂", "放松", "轻音乐", "古典"])
        
        assert result.is_valid
        assert "放松" in result.tags
    
    def test_parse_returns_empty_for_no_match(self):
        """测试无匹配时返回空查询"""
        response = '{"matched_tags": [], "match_mode": "any", "confidence": 0.1, "reason": "无法匹配任何标签"}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("播放随机音乐", ["流行", "摇滚"])
        
        assert not result.is_valid
        assert len(result.tags) == 0
    
    def test_parse_filters_invalid_tags(self):
        """测试过滤无效标签"""
        response = '{"matched_tags": ["流行", "不存在的标签", "摇滚"], "match_mode": "any", "confidence": 0.8}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("来点音乐", ["流行", "摇滚", "古典"])
        
        assert "流行" in result.tags
        assert "摇滚" in result.tags
        assert "不存在的标签" not in result.tags
    
    def test_parse_case_insensitive_matching(self):
        """测试不区分大小写匹配"""
        response = '{"matched_tags": ["ROCK", "pop"], "match_mode": "any", "confidence": 0.8}'
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("来点音乐", ["Rock", "Pop", "Jazz"])
        
        assert len(result.tags) == 2
        # 应该返回原始大小写
        assert "Rock" in result.tags or "Pop" in result.tags
    
    def test_parse_handles_json_with_code_fences(self):
        """测试处理带代码块的 JSON"""
        response = '''```json
{"matched_tags": ["流行"], "match_mode": "any", "confidence": 0.8}
```'''
        client = _FakeClient(response)
        parser = TagQueryParser(client)
        
        result = parser.parse("听点流行音乐", ["流行", "摇滚"])
        
        assert result.is_valid
        assert "流行" in result.tags
    
    def test_parse_handles_empty_instruction(self):
        """测试处理空指令"""
        client = _FakeClient('{"matched_tags": []}')
        parser = TagQueryParser(client)
        
        result = parser.parse("", ["流行", "摇滚"])
        
        assert not result.is_valid
    
    def test_parse_handles_empty_available_tags(self):
        """测试处理空可用标签"""
        client = _FakeClient('{"matched_tags": []}')
        parser = TagQueryParser(client)
        
        result = parser.parse("听点音乐", [])
        
        assert not result.is_valid
        assert "没有可用标签" in result.reason
    
    def test_parse_handles_invalid_json(self):
        """测试处理无效 JSON"""
        client = _FakeClient('not a json')
        parser = TagQueryParser(client)
        
        result = parser.parse("听点音乐", ["流行"])
        
        assert not result.is_valid
        assert "解析失败" in result.reason or "非 JSON" in result.reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
