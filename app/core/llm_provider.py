import httpx
import json
from typing import Dict, Any, AsyncGenerator
from enum import Enum

from fastapi import HTTPException

from app.models.enums import Provider
from app.core.config import settings
from app.utils.logging import logger

# Configuration des providers
PROVIDER_CONFIGS = {
    Provider.MISTRAL: {
        "base_url": "https://api.mistral.ai/v1/chat/completions",
        "model": "mistral-medium",
        "headers_key": "Authorization",
        "headers_prefix": "Bearer"
    },
    Provider.OPENAI: {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "headers_key": "Authorization",
        "headers_prefix": "Bearer"
    },
    Provider.ANTHROPIC: {
        "base_url": "https://api.anthropic.com/v1/messages",
        "model": "claude-3-haiku-20240307",
        "headers_key": "x-api-key",
        "headers_prefix": ""
    },
    Provider.DEEPSEEK: {
        "base_url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "headers_key": "Authorization",
        "headers_prefix": "Bearer"
    },
    Provider.GROQ: {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "mixtral-8x7b-32768",
        "headers_key": "Authorization",
        "headers_prefix": "Bearer"
    }
}

# Clés API
API_KEYS = {
    Provider.MISTRAL: settings.MISTRAL_API_KEY,
    Provider.OPENAI: settings.OPENAI_API_KEY,
    Provider.ANTHROPIC: settings.ANTHROPIC_API_KEY,
    Provider.DEEPSEEK: settings.DEEPSEEK_API_KEY,
    Provider.GROQ: settings.GROQ_API_KEY
}


# Provider LLM optimisé
class OptimizedLLMProvider:
    def __init__(self, provider: Provider):
        self.provider = provider
        self.config = PROVIDER_CONFIGS[provider]
        self.api_key = API_KEYS[provider]
        self.client = None

    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            key = self.config["headers_key"]
            prefix = self.config["headers_prefix"]
            if prefix:
                headers[key] = f"{prefix} {self.api_key}"
            else:
                headers[key] = self.api_key
        return headers

    def format_messages(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> Dict[str, Any]:
        if self.provider == Provider.ANTHROPIC:
            return {
                "model": self.config["model"],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
        else:
            return {
                "model": self.config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

    def extract_response(self, response_data: Dict[str, Any]) -> str:
        if self.provider == Provider.ANTHROPIC:
            return response_data["content"][0]["text"]
        else:
            return response_data["choices"][0]["message"]["content"]

    async def generate_response(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise ValueError(f"Clé API manquante pour {self.provider}")

        headers = self.get_headers()
        data = self.format_messages(prompt, **kwargs)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.config["base_url"],
                headers=headers,
                json=data
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Erreur API {self.provider}: {response.text}"
                )

            response_data = response.json()
            return self.extract_response(response_data)

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Génère une réponse en streaming."""
        if not self.api_key:
            raise ValueError(f"Clé API manquante pour {self.provider}")

        headers = self.get_headers()
        data = self.format_messages(prompt)
        data["stream"] = True

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                    'POST',
                    self.config["base_url"],
                    headers=headers,
                    json=data
            ) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Erreur API {self.provider}: {response.text}"
                    )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data_json = json.loads(data_str)
                            if self.provider == Provider.ANTHROPIC:
                                if data_json.get("type") == "content_block_delta":
                                    yield data_json["delta"]["text"]
                            else:
                                if "choices" in data_json and len(data_json["choices"]) > 0:
                                    delta = data_json["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                        except json.JSONDecodeError:
                            continue
