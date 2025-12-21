"""
LLM Provider Abstraction Layer

Defines a generic LLM client interface, supporting a unified calling protocol for multiple service providers.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Sequence

logger = logging.getLogger(__name__)


class LLMProviderError(RuntimeError):
    """Base class for LLM provider errors"""
    pass


@dataclass(frozen=True)
class LLMSettings:
    """Generic LLM Settings Base Class
    
    Attributes:
        api_key: API key
        model: Model name
        timeout_seconds: Request timeout in seconds
        temperature: Sampling temperature
        max_tokens: Maximum number of generated tokens
        json_mode: Whether to enable JSON mode
        extra: Provider-specific additional configurations
    """
    api_key: str
    model: str
    timeout_seconds: float = 30.0
    temperature: float = 0.2
    max_tokens: int = 512
    json_mode: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """LLM Provider Abstract Interface
    
    All LLM service provider clients must implement this interface.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'siliconflow', 'gemini')"""
        ...
    
    @property
    @abstractmethod
    def settings(self) -> LLMSettings:
        """Current settings"""
        ...
    
    @abstractmethod
    def chat_completions(self, messages: Sequence[Dict[str, str]]) -> str:
        """Execute a chat completion request
        
        Args:
            messages: List of messages in OpenAI format, each containing 'role' and 'content'.
                     Available roles: 'system', 'user', 'assistant'
        
        Returns:
            The text content of the assistant's reply
        
        Raises:
            LLMProviderError: When the API call fails
        """
        ...
    
    def validate_connection(self) -> bool:
        """Validate if the connection is available (optional implementation)
        
        Returns:
            True if the connection is valid
        """
        return True
