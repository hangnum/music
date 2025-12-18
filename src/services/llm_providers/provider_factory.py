"""
LLM 提供商工厂

根据配置创建对应的 LLM 提供商实例。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.llm_provider import LLMProvider, LLMProviderError

if TYPE_CHECKING:
    from services.config_service import ConfigService

logger = logging.getLogger(__name__)

# 可用的提供商列表
AVAILABLE_PROVIDERS = ["siliconflow", "gemini"]


def create_llm_provider(config: "ConfigService") -> LLMProvider:
    """根据配置创建 LLM 提供商实例
    
    Args:
        config: 配置服务实例
    
    Returns:
        对应的 LLM 提供商实例
    
    Raises:
        LLMProviderError: 当提供商未知或配置错误时
    """
    provider_name = str(config.get("llm.provider", "siliconflow")).strip().lower()
    
    logger.info(f"Creating LLM provider: {provider_name}")
    
    if provider_name == "siliconflow":
        from .siliconflow_provider import SiliconFlowProvider
        return SiliconFlowProvider.from_config(config)
    elif provider_name == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider.from_config(config)
    else:
        available = ", ".join(AVAILABLE_PROVIDERS)
        raise LLMProviderError(
            f"未知的 LLM 提供商: {provider_name}。可用选项: {available}"
        )
