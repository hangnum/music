# -*- coding: utf-8 -*-
"""
LLM 提供商端口接口

定义 LLM 服务的抽象接口，使应用不依赖具体的 LLM 实现。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Sequence, runtime_checkable


@dataclass
class LLMSettings:
    """LLM 设置"""
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048


@runtime_checkable
class ILLMProvider(Protocol):
    """LLM 提供商接口
    
    提供聊天补全功能的统一接口。
    当前实现：SiliconFlowClient, GeminiClient
    """
    
    @property
    def name(self) -> str:
        """提供商名称（如 'siliconflow', 'gemini'）"""
        ...
    
    @property
    def settings(self) -> LLMSettings:
        """当前设置"""
        ...
    
    def chat_completions(
        self, 
        messages: Sequence[Dict[str, str]]
    ) -> str:
        """执行聊天补全
        
        Args:
            messages: 消息列表，每条消息包含 'role' 和 'content'
                     role 可以是 'system', 'user', 'assistant'
            
        Returns:
            助手的回复内容
            
        Raises:
            Exception: API 调用失败时抛出
        """
        ...
    
    def is_available(self) -> bool:
        """检查服务是否可用
        
        Returns:
            服务是否可用
        """
        ...


@runtime_checkable 
class ILLMProviderFactory(Protocol):
    """LLM 提供商工厂接口"""
    
    def create(
        self, 
        provider_name: str, 
        settings: Optional[LLMSettings] = None
    ) -> ILLMProvider:
        """创建 LLM 提供商实例
        
        Args:
            provider_name: 提供商名称
            settings: 可选的设置覆盖
            
        Returns:
            提供商实例
        """
        ...
    
    def get_available_providers(self) -> List[str]:
        """获取可用的提供商列表"""
        ...
