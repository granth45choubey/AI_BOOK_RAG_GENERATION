"""
LLM routing helper.

Selects a provider and model based on config and role.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Role = Literal["reasoning", "light"]


def _model_for(role: Role) -> str:
    if role == "light":
        return settings.llm_light_model or settings.llm_reasoning_model
    return settings.llm_reasoning_model or settings.ollama_model


@lru_cache(maxsize=4)
def get_llm(role: Role = "reasoning"):
    provider = settings.llm_provider.lower().strip()
    model = _model_for(role)
    base_url = settings.llm_api_base_url.strip() or None

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        logger.info("LLM: Ollama | role=%s | model=%s | url=%s", role, model, settings.ollama_base_url)
        return ChatOllama(
            model=model,
            base_url=settings.ollama_base_url,
            temperature=0.3,
        )

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain_openai is required for OpenAI provider. "
                "Install with: pip install langchain-openai"
            ) from exc
        kwargs = {"model": model, "temperature": 0.3}
        if base_url:
            kwargs["base_url"] = base_url
        logger.info("LLM: OpenAI | role=%s | model=%s", role, model)
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ImportError(
                "langchain_anthropic is required for Anthropic provider. "
                "Install with: pip install langchain-anthropic"
            ) from exc
        kwargs = {"model": model, "temperature": 0.3}
        if base_url:
            kwargs["base_url"] = base_url
        logger.info("LLM: Anthropic | role=%s | model=%s", role, model)
        return ChatAnthropic(**kwargs)

    raise ValueError(f"Unsupported llm_provider: {provider!r}")
