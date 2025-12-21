"""
SiliconFlow Provider Implementation

Based on the OpenAI-compatible Chat Completions API.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.llm_provider import LLMProvider, LLMProviderError, LLMSettings
from services.config_service import ConfigService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SiliconFlowSettings(LLMSettings):
    """SiliconFlow specific settings.
    
    Attributes:
        base_url: API base URL.
        api_key_env: Environment variable name for the API key.
    """
    base_url: str = "https://api.siliconflow.cn/v1"
    api_key_env: str = "SILICONFLOW_API_KEY"


class SiliconFlowProvider(LLMProvider):
    """SiliconFlow OpenAI-compatible Chat Completions Provider.
    
    Endpoint: {base_url}/chat/completions
    Auth: Authorization: Bearer <api_key>
    """
    
    def __init__(self, settings: SiliconFlowSettings):
        self._settings = settings
    
    @property
    def name(self) -> str:
        return "siliconflow"
    
    @property
    def settings(self) -> SiliconFlowSettings:
        return self._settings
    
    @staticmethod
    def from_config(config: ConfigService) -> "SiliconFlowProvider":
        """Create a provider instance from the configuration service."""
        base_url = config.get("llm.siliconflow.base_url", "https://api.siliconflow.cn/v1")
        model = config.get("llm.siliconflow.model", "Qwen/Qwen2.5-7B-Instruct")
        api_key_env = config.get("llm.siliconflow.api_key_env", "SILICONFLOW_API_KEY")
        api_key = config.get("llm.siliconflow.api_key", "") or os.environ.get(api_key_env, "")
        timeout_seconds = float(config.get("llm.siliconflow.timeout_seconds", 20.0))
        temperature = float(config.get("llm.queue_manager.temperature", 0.2))
        max_tokens = int(config.get("llm.queue_manager.max_tokens", 512))
        json_mode = bool(config.get("llm.queue_manager.json_mode", True))
        
        if not api_key:
            raise LLMProviderError(
                f"Missing SiliconFlow API Key: please provide it in configuration `llm.siliconflow.api_key` or environment variable `{api_key_env}`."
            )
        
        return SiliconFlowProvider(
            SiliconFlowSettings(
                api_key=str(api_key),
                model=str(model),
                timeout_seconds=timeout_seconds,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                base_url=str(base_url),
                api_key_env=str(api_key_env),
            )
        )
    
    def chat_completions(self, messages: Sequence[Dict[str, str]]) -> str:
        """Execute chat completion request."""
        url = self._settings.base_url.rstrip("/") + "/chat/completions"
        
        payload: Dict[str, Any] = {
            "model": self._settings.model,
            "messages": list(messages),
            "temperature": self._settings.temperature,
            "max_tokens": self._settings.max_tokens,
        }
        if self._settings.json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        req = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._settings.api_key}",
            },
            method="POST",
        )
        
        logger.debug(f"SiliconFlow request to {url} with model {self._settings.model}")
        
        try:
            with urlopen(req, timeout=self._settings.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.error(f"SiliconFlow API HTTP {e.code}: {body or e.reason}")
            raise LLMProviderError(f"SiliconFlow API HTTP {e.code}: {body or e.reason}") from e
        except URLError as e:
            logger.error(f"SiliconFlow API request failed: {e.reason}")
            raise LLMProviderError(f"SiliconFlow API request failed: {e.reason}") from e
        
        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            logger.debug(f"SiliconFlow response: {content[:200]}...")
            return content
        except Exception as e:
            logger.error(f"SiliconFlow response parsing failed: {raw[:400]}")
            raise LLMProviderError(f"SiliconFlow response parsing failed: {raw[:400]}") from e
    
    def validate_connection(self) -> bool:
        """Validate if the API connection is functional."""
        try:
            # Use explicit JSON prompt to avoid non-JSON responses in JSON mode.
            self.chat_completions([{
                "role": "user", 
                "content": 'Respond with this exact JSON: {"status": "ok"}'
            }])
            return True
        except LLMProviderError:
            return False
