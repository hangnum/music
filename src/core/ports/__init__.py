# -*- coding: utf-8 -*-
"""
端口接口包

定义应用程序与外部基础设施（数据库、音频引擎、LLM）之间的接口。

设计原则：
- 使用 Protocol 定义接口，支持结构化子类型
- 服务层依赖这些接口而非具体实现
- 便于测试时使用 fake/mock 替换
"""

from core.ports.database import IDatabase, ITrackRepository
from core.ports.audio import IAudioEngine
from core.ports.llm import ILLMProvider

__all__ = [
    "IDatabase",
    "ITrackRepository", 
    "IAudioEngine",
    "ILLMProvider",
]
