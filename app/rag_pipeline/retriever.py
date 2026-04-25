"""
ChromaDB storage and retrieval module.

Design: NO embedding_function is passed to the Chroma collection.
Instead, we embed texts ourselves using OllamaEmbeddings and pass the raw
float vectors directly via the `embeddings=` / `query_embeddings=` params.

This avoids every wrapper-compatibility issue (ChromaDB's EmbeddingFunction
protocol requires a `name` attribute that LangChain wrappers don't expose).

Responsibilities
----------------
- Obtain (or create) the Chroma collection (metadata-only, no built-in EF).
- Embed chunk texts with LangChain OllamaEmbeddings → store in Chroma.
- Embed a query string → Chroma top-k similarity search → return dicts.
"""
from __future__ import annotations

import logging
import uuid
from functools import lru_cache
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.rag_pipeline.embedder import get_embedding_function
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Chroma client ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_chroma_client() -> chromadb.PersistentClient:
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    logger.info("ChromaDB client ready at '%s'", settings.chroma_persist_dir)
    return client


# ── Collection (no embedding_function — we embed manually) ────────────────────

def get_collection():
    """
    Return (or create) the Chroma collection.

    We deliberately do NOT pass embedding_function so ChromaDB never tries to
    call our wrapper.  All embedding is done explicitly before each upsert/query.
    """
    client = _get_chroma_client()
    collection = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        # cosine distance → score = 1 - distance (higher = more similar)
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ── Write ─────────────────────────────────────────────────────────────────────

def store_chunks(chunks: List[Dict[str, Any]]) -> int:
    """
    Embed and persist chunks in ChromaDB.

    Parameters
    ----------
    chunks : list of dicts with keys: text, source, page, chunk_index

    Returns
    -------
    Number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_collection()
    ef = get_embedding_function()   # langchain_community OllamaEmbeddings

    texts = [c["text"] for c in chunks]
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "source": c["source"],
            "page": int(c["page"]),
            "chunk_index": int(c["chunk_index"]),
        }
        for c in chunks
    ]

    # Upsert in batches of 50.  Sending too many texts to Ollama in a single
    # embed_documents() call can itself time out — smaller batches are safer
    # and give per-batch progress visibility in the logs.
    batch_size = 50
    total_stored = 0
    n_batches = (len(ids) + batch_size - 1) // batch_size

    for batch_num, i in enumerate(range(0, len(ids), batch_size), start=1):
        batch_texts = texts[i : i + batch_size]

        logger.info(
            "Embedding batch %d/%d (%d texts)…",
            batch_num, n_batches, len(batch_texts),
        )

        # ── Embed this batch explicitly ───────────────────────────────────
        batch_vectors: List[List[float]] = ef.embed_documents(batch_texts)

        collection.upsert(
            ids=ids[i : i + batch_size],
            documents=batch_texts,
            embeddings=batch_vectors,          # ← raw vectors, no wrapper needed
            metadatas=metadatas[i : i + batch_size],
        )
        total_stored += len(batch_texts)


    logger.info(
        "Stored %d chunks in collection '%s'",
        total_stored,
        settings.chroma_collection_name,
    )
    return total_stored


# ── Read ──────────────────────────────────────────────────────────────────────

def retrieve_chunks(
    query: str,
    top_k: int | None = None,
    filter_metadata: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the top-k most similar chunks for a query.

    Parameters
    ----------
    query : natural-language query string
    top_k : number of results (falls back to settings)
    filter_metadata : optional ChromaDB where-filter  e.g. {"source": "doc.pdf"}

    Returns
    -------
    list of dicts: {text, source, page, chunk_index, score}
    """
    top_k = top_k or settings.retrieval_top_k
    collection = get_collection()

    count = collection.count()
    if count == 0:
        logger.warning("Collection is empty — no documents have been ingested yet.")
        return []

    n_results = min(top_k, count)
    ef = get_embedding_function()

    # ── Embed the query explicitly ─────────────────────────────────────────
    query_vector: List[float] = ef.embed_query(query)

    kwargs: Dict[str, Any] = {
        "query_embeddings": [query_vector],    # ← raw vector, no wrapper needed
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if filter_metadata:
        kwargs["where"] = filter_metadata

    results = collection.query(**kwargs)

    retrieved: List[Dict[str, Any]] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        retrieved.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "page": meta.get("page", -1),
            "chunk_index": meta.get("chunk_index", -1),
            "score": round(1 - float(dist), 4),   # cosine sim (higher = better)
        })

    logger.info("Retrieved %d chunks for query: %.60s…", len(retrieved), query)
    return retrieved
