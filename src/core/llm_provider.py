"""
LLM 提供商抽象层

定义通用的 LLM 客户端接口，支持多个服务商的统一调用协议。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Sequence

logger = logging.getLogger(__name__)


class LLMProviderError(RuntimeError):
    """LLM 提供商错误基类"""
    pass


@dataclass(frozen=True)
class LLMSettings:
    """通用 LLM 设置基类
    
    Attributes:
        api_key: API 密钥
        model: 模型名称
        timeout_seconds: 请求超时时间（秒）
        temperature: 采样温度
        max_tokens: 最大生成 token 数
        json_mode: 是否启用 JSON 模式
        extra: 提供商特定的额外配置
    """
    api_key: str
    model: str
    timeout_seconds: float = 30.0
    temperature: float = 0.2
    max_tokens: int = 512
    json_mode: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """LLM 提供商抽象接口
    
    所有 LLM 服务商客户端必须实现此接口。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """提供商标识符（如 'siliconflow', 'gemini'）"""
        ...
    
    @property
    @abstractmethod
    def settings(self) -> LLMSettings:
        """当前设置"""
        ...
    
    @abstractmethod
    def chat_completions(self, messages: Sequence[Dict[str, str]]) -> str:
        """执行聊天补全请求
        
        Args:
            messages: OpenAI 格式的消息列表，每条消息包含 'role' 和 'content'
                     role 可选值: 'system', 'user', 'assistant'
        
        Returns:
            助手回复的文本内容
        
        Raises:
            LLMProviderError: 当 API 调用失败时
        """
        ...
    
    def validate_connection(self) -> bool:
        """验证连接是否可用（可选实现）
        
        Returns:
            True 如果连接有效
        """
        return True
