"""
LLM Provider Factory

Creates the corresponding LLM provider instance based on configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.llm_provider import LLMProvider, LLMProviderError

if TYPE_CHECKING:
    from services.config_service import ConfigService

logger = logging.getLogger(__name__)

# List of available providers
AVAILABLE_PROVIDERS = ["siliconflow", "gemini"]


def create_llm_provider(config: "ConfigService") -> LLMProvider:
    """Create an LLM provider instance based on configuration.
    
    Args:
        config: Configuration service instance.
    
    Returns:
        The corresponding LLM provider instance.
    
    Raises:
        LLMProviderError: If the provider is unknown or configuration is incorrect.
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
            f"Unknown LLM provider: {provider_name}. Available options: {available}"
        )
