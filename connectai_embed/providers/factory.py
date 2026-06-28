from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .anthropic import AnthropicProvider
from .base import LLMProvider
from .gemini import GeminiProvider
from .openai import OpenAIProvider

if TYPE_CHECKING:
    from ..types import AgentConfig

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5-20250929",
    "openai": "gpt-4o",
    "gemini": "gemini-2.0-flash",
}

_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def create_provider(config: AgentConfig) -> LLMProvider:
    provider_type = config.provider or "anthropic"
    api_key = config.api_key or os.environ.get(_ENV_KEYS.get(provider_type, ""), "")
    model = config.model or os.environ.get("CDATA_LLM_MODEL", "") or _DEFAULT_MODELS.get(provider_type, "")
    max_tokens = config.max_tokens
    temperature = config.temperature
    base_url = config.api_base_url

    kwargs: dict = {
        "api_key": api_key,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if base_url:
        kwargs["base_url"] = base_url

    if provider_type == "anthropic":
        return AnthropicProvider(**kwargs)
    elif provider_type == "openai":
        return OpenAIProvider(**kwargs)
    elif provider_type == "gemini":
        return GeminiProvider(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
