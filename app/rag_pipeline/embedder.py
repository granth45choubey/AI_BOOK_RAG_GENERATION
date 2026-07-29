"""
Embedding module.

Supports:
- "ollama" : Native Ollama /api/embed batch API (default, no API key needed)
- Future   : OpenAI / HuggingFace via LangChain wrappers

Public API
----------
  embed_documents(texts)  → List[List[float]]  — batched for ingestion
  embed_query(text)       → List[float]         — single query vector
  embed_texts(texts)      → alias for embed_documents
  get_embedding_function()→ LangChain wrapper (legacy / non-Ollama providers)
"""
from __future__ import annotations

import logging
import warnings
from functools import lru_cache
from typing import List

import httpx

warnings.filterwarnings("ignore", message=".*OllamaEmbeddings.*")

from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def _ollama_http_client() -> httpx.Client:
    """Reused HTTP client for Ollama embedding requests."""
    return httpx.Client(
        base_url=settings.ollama_base_url,
        timeout=httpx.Timeout(settings.ollama_embed_timeout, connect=10.0),
    )


def _embed_ollama_native(texts: List[str]) -> List[List[float]]:
    """
    Embed texts using Ollama's native /api/embed endpoint.

    Unlike LangChain's OllamaEmbeddings (one HTTP call per text), Ollama
    accepts a list input and embeds the full batch in a single request —
    typically 30–40× faster for document ingestion workloads.
    """
    if not texts:
        return []

    client = _ollama_http_client()
    batch_size = max(1, settings.embedding_batch_size)
    all_vectors: List[List[float]] = []
    n_batches = (len(texts) + batch_size - 1) // batch_size

    for batch_num, start in enumerate(range(0, len(texts), batch_size), start=1):
        batch = texts[start : start + batch_size]
        response = client.post(
            "/api/embed",
            json={"model": settings.embedding_model, "input": batch},
        )
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embeddings")
        if not embeddings or len(embeddings) != len(batch):
            raise RuntimeError(
                f"Ollama /api/embed returned {len(embeddings or [])} vectors "
                f"for {len(batch)} inputs (batch {batch_num}/{n_batches})."
            )
        all_vectors.extend(embeddings)
        logger.debug(
            "Ollama embed batch %d/%d (%d texts)",
            batch_num, n_batches, len(batch),
        )

    return all_vectors


@lru_cache(maxsize=1)
def get_embedding_function():
    """
    Return a cached LangChain embedding function.

    Used as fallback for non-Ollama providers.  Ingestion paths should prefer
    embed_documents() / embed_query() which use the native Ollama batch API.
    """
    from langchain_community.embeddings import OllamaEmbeddings

    provider = settings.embedding_provider.lower()

    if provider == "ollama":
        logger.info(
            "LangChain embedding fallback: Ollama | model: %s | url: %s",
            settings.embedding_model,
            settings.ollama_base_url,
        )
        return OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )

    raise ValueError(f"Unsupported embedding provider: {provider!r}")


def embed_documents(texts: List[str]) -> List[List[float]]:
    """Embed a list of strings; uses native Ollama batch API when configured."""
    if not texts:
        return []

    provider = settings.embedding_provider.lower()
    if provider == "ollama":
        return _embed_ollama_native(texts)

    ef = get_embedding_function()
    return ef.embed_documents(texts)


def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    return embed_documents([text])[0]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Alias kept for backward compatibility."""
    return embed_documents(texts)
