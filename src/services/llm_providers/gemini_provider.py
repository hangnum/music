"""
Google Gemini 提供商实现

使用 Gemini API (generateContent) 提供聊天补全功能。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.llm_provider import LLMProvider, LLMProviderError, LLMSettings
from services.config_service import ConfigService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeminiSettings(LLMSettings):
    """Google Gemini 特定设置
    
    Attributes:
        base_url: API 基础 URL
        api_key_env: 环境变量名称（用于获取 API Key）
    """
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    api_key_env: str = "GOOGLE_GEMINI_API_KEY"


class GeminiProvider(LLMProvider):
    """Google Gemini API 提供商
    
    Endpoint: {base_url}/models/{model}:generateContent
    Auth: ?key=<api_key> (URL parameter)
    
    消息格式转换：
    - OpenAI 'system' role -> Gemini 系统指令 (systemInstruction)
    - OpenAI 'user'/'assistant' -> Gemini 'user'/'model'
    """
    
    def __init__(self, settings: GeminiSettings):
        self._settings = settings
    
    @property
    def name(self) -> str:
        return "gemini"
    
    @property
    def settings(self) -> GeminiSettings:
        return self._settings
    
    @staticmethod
    def from_config(config: ConfigService) -> "GeminiProvider":
        """从配置服务创建提供商实例"""
        base_url = config.get("llm.gemini.base_url", "https://generativelanguage.googleapis.com/v1beta")
        model = config.get("llm.gemini.model", "gemini-2.0-flash")
        api_key_env = config.get("llm.gemini.api_key_env", "GOOGLE_GEMINI_API_KEY")
        api_key = config.get("llm.gemini.api_key", "") or os.environ.get(api_key_env, "")
        timeout_seconds = float(config.get("llm.gemini.timeout_seconds", 30.0))
        temperature = float(config.get("llm.queue_manager.temperature", 0.2))
        max_tokens = int(config.get("llm.queue_manager.max_tokens", 512))
        json_mode = bool(config.get("llm.queue_manager.json_mode", True))
        
        if not api_key:
            raise LLMProviderError(
                f"缺少 Gemini API Key：请在配置 `llm.gemini.api_key` 或环境变量 `{api_key_env}` 中提供"
            )
        
        return GeminiProvider(
            GeminiSettings(
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
    
    def _convert_messages_to_gemini_format(
        self, messages: Sequence[Dict[str, str]]
    ) -> tuple[str | None, List[Dict[str, Any]]]:
        """将 OpenAI 消息格式转换为 Gemini 格式
        
        Returns:
            (system_instruction, contents)
        """
        system_instruction: str | None = None
        contents: List[Dict[str, Any]] = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # Gemini 使用 systemInstruction 字段
                system_instruction = content
            elif role == "assistant":
                # Gemini 使用 "model" 作为助手角色
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
            else:
                # user 或其他角色映射到 user
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
        
        return system_instruction, contents
    
    def chat_completions(self, messages: Sequence[Dict[str, str]]) -> str:
        """执行聊天补全请求"""
        url = f"{self._settings.base_url.rstrip('/')}/models/{self._settings.model}:generateContent"
        url_with_key = f"{url}?key={self._settings.api_key}"
        
        system_instruction, contents = self._convert_messages_to_gemini_format(messages)
        
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self._settings.temperature,
                "maxOutputTokens": self._settings.max_tokens,
            }
        }
        
        # 添加系统指令
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # JSON 模式：Gemini 使用 responseMimeType
        if self._settings.json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        
        req = Request(
            url_with_key,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )
        
        logger.debug(f"Gemini request to {url} with model {self._settings.model}")
        
        try:
            with urlopen(req, timeout=self._settings.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.error(f"Gemini API HTTP {e.code}: {body or e.reason}")
            raise LLMProviderError(f"Gemini API HTTP {e.code}: {body or e.reason}") from e
        except URLError as e:
            logger.error(f"Gemini API 请求失败: {e.reason}")
            raise LLMProviderError(f"Gemini API 请求失败: {e.reason}") from e
        
        try:
            data = json.loads(raw)
            # Gemini 响应格式: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMProviderError(f"Gemini 未返回候选结果: {raw[:400]}")
            
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise LLMProviderError(f"Gemini 响应缺少 parts: {raw[:400]}")
            
            content = parts[0].get("text", "")
            logger.debug(f"Gemini response: {content[:200]}...")
            return content
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Gemini 响应解析失败: {raw[:400]}")
            raise LLMProviderError(f"Gemini 响应解析失败: {raw[:400]}") from e
    
    def validate_connection(self) -> bool:
        """验证 API 连接是否有效"""
        try:
            # 使用明确的 JSON 提示词，避免 json_mode 下返回非 JSON
            self.chat_completions([{
                "role": "user", 
                "content": 'Respond with this exact JSON: {"status": "ok"}'
            }])
            return True
        except LLMProviderError:
            return False
