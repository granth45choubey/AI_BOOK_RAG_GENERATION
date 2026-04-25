"""
Embedding module.

Supports:
- "ollama" : OllamaEmbeddings via langchain_community (default, no API key needed)

Provides standard LangChain embedding interface:
  embed_documents(texts)  → List[List[float]]
  embed_query(text)       → List[float]

Adding a new provider is as simple as extending _get_embedding_function().
"""
from __future__ import annotations

import logging
import warnings
from functools import lru_cache
from typing import List

# langchain_community.OllamaEmbeddings is deprecated in LC>=0.3.1 but fully
# functional — suppress the noisy warning so server logs stay clean.
# We filter both DeprecationWarning and its LangChain subclass.
warnings.filterwarnings("ignore", message=".*OllamaEmbeddings.*")

from langchain_community.embeddings import OllamaEmbeddings  # noqa: E402

from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def get_embedding_function():
    """Return a cached embedding function based on config."""
    provider = settings.embedding_provider.lower()

    if provider == "ollama":
        logger.info(
            "Embedding provider: Ollama | model: %s | base_url: %s",
            settings.embedding_model,
            settings.ollama_base_url,
        )
        return OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )

    # ── Future providers (uncomment and set EMBEDDING_PROVIDER in .env) ────
    # elif provider == "openai":
    #     from langchain_openai import OpenAIEmbeddings
    #     return OpenAIEmbeddings(model="text-embedding-3-small")
    # elif provider == "huggingface":
    #     from langchain_huggingface import HuggingFaceEmbeddings
    #     return HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    raise ValueError(f"Unsupported embedding provider: {provider!r}")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of strings and return float vectors."""
    ef = get_embedding_function()
    vectors = ef.embed_documents(texts)
    logger.debug("Embedded %d texts → vector dim %d", len(texts), len(vectors[0]) if vectors else 0)
    return vectors
