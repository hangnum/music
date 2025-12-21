# -*- coding: utf-8 -*-
"""
LLM Provider Port Interface

Defines an abstract interface for LLM services, ensuring the application does not 
depend on specific LLM implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Sequence, runtime_checkable


@dataclass
class LLMSettings:
    """LLM Settings"""
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048


@runtime_checkable
class ILLMProvider(Protocol):
    """LLM Provider Interface
    
    Provides a unified interface for chat completion functionality.
    Current implementations: SiliconFlowClient, GeminiClient
    """
    
    @property
    def name(self) -> str:
        """Provider name (e.g., 'siliconflow', 'gemini')"""
        ...
    
    @property
    def settings(self) -> LLMSettings:
        """Current settings"""
        ...
    
    def chat_completions(
        self, 
        messages: Sequence[Dict[str, str]]
    ) -> str:
        """Execute chat completion
        
        Args:
            messages: List of messages, each containing 'role' and 'content'.
                     Role can be 'system', 'user', 'assistant'.
            
        Returns:
            The assistant's reply content
            
        Raises:
            Exception: Thrown when the API call fails
        """
        ...
    
    def is_available(self) -> bool:
        """Check if the service is available
        
        Returns:
            True if the service is available
        """
        ...


@runtime_checkable 
class ILLMProviderFactory(Protocol):
    """LLM Provider Factory Interface"""
    
    def create(
        self, 
        provider_name: str, 
        settings: Optional[LLMSettings] = None
    ) -> ILLMProvider:
        """Create an LLM provider instance
        
        Args:
            provider_name: Name of the provider
            settings: Optional settings override
            
        Returns:
            An LLM provider instance
        """
        ...
    
    def get_available_providers(self) -> List[str]:
        """Get a list of available providers"""
        ...
