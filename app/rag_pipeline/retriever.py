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
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional

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
    Backward-compatible wrapper — tags chunks as source_type="general".
    """
    return store_chunks_with_type(chunks, source_type="general", priority_score=0.5)


def store_chunks_with_type(
    chunks: List[Dict[str, Any]],
    source_type: str = "general",
    priority_score: float = 0.5,
) -> int:
    """
    Embed and persist chunks with explicit source_type and priority_score metadata.

    Parameters
    ----------
    chunks      : list of dicts with keys: text, source, page, chunk_index
    source_type : "author" | "context" | "outline" | "competitor" | "general"
    priority_score : float 0–1; higher = retrieved first in layered pipeline

    Returns
    -------
    Number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_collection()
    ef = get_embedding_function()

    texts = [c["text"] for c in chunks]
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "source":         c["source"],
            "page":           int(c["page"]),
            "chunk_index":    int(c["chunk_index"]),
            "source_type":    source_type,
            "priority_score": priority_score,
        }
        for c in chunks
    ]

    batch_size = 50
    total_stored = 0
    n_batches = (len(ids) + batch_size - 1) // batch_size

    for batch_num, i in enumerate(range(0, len(ids), batch_size), start=1):
        batch_texts = texts[i : i + batch_size]
        logger.info(
            "Embedding batch %d/%d (%d texts, source_type=%s)…",
            batch_num, n_batches, len(batch_texts), source_type,
        )
        batch_vectors: List[List[float]] = ef.embed_documents(batch_texts)
        collection.upsert(
            ids=ids[i : i + batch_size],
            documents=batch_texts,
            embeddings=batch_vectors,
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


# ── Structured context dataclass ─────────────────────────────────────────────────

@dataclass
class StructuredContext:
    """Layered context assembled by retrieve_layered()."""
    author_chunks:     List[Dict[str, Any]] = field(default_factory=list)
    book_context_text: Optional[str]        = None
    outline_text:      Optional[str]        = None
    competitor_chunks: List[Dict[str, Any]] = field(default_factory=list)
    general_chunks:    List[Dict[str, Any]] = field(default_factory=list)


# ── Layered retrieval ─────────────────────────────────────────────────────────

def _get_doc_by_id(doc_id: str) -> Optional[str]:
    """Fetch a specific document by its ChromaDB ID. Returns text or None."""
    try:
        result = get_collection().get(ids=[doc_id], include=["documents"])
        docs = result.get("documents") or []
        return docs[0] if docs and docs[0] else None
    except Exception:
        return None


def _retrieve_by_type(
    query_vector: List[float],
    source_type: str,
    top_k: int,
) -> List[Dict[str, Any]]:
    """
    Retrieve chunks filtered by source_type metadata.
    Returns [] gracefully if no matching documents exist.
    """
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    # Binary-search down n_results if ChromaDB rejects our request because
    # fewer docs of this source_type exist than we asked for.
    n = min(top_k, count)
    while n >= 1:
        try:
            res = collection.query(
                query_embeddings=[query_vector],
                n_results=n,
                where={"source_type": {"$eq": source_type}},
                include=["documents", "metadatas", "distances"],
            )
            chunks = []
            for doc, meta, dist in zip(
                res["documents"][0],
                res["metadatas"][0],
                res["distances"][0],
            ):
                chunks.append({
                    "text":        doc,
                    "source":      meta.get("source", "unknown"),
                    "page":        meta.get("page", -1),
                    "chunk_index": meta.get("chunk_index", -1),
                    "source_type": meta.get("source_type", source_type),
                    "score":       round(1 - float(dist), 4),
                })
            return chunks
        except Exception as exc:
            err = str(exc).lower()
            # ChromaDB raises when n_results > number of filtered results
            if "number of results" in err or "n_results" in err or "less than" in err:
                n -= 1
                continue
            logger.warning("retrieve_by_type(%s) failed: %s", source_type, exc)
            return []
    return []


def _retrieve_competitor_chunks(
    query_vector: List[float],
    top_k: int,
) -> List[Dict[str, Any]]:
    """Query the separate competitor_docs ChromaDB collection."""
    try:
        client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        col = client.get_or_create_collection(
            name=settings.competitor_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        count = col.count()
        if count == 0:
            return []
        n = min(top_k, count)
        res = col.query(
            query_embeddings=[query_vector],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for doc, meta, dist in zip(
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0],
        ):
            chunks.append({
                "text":        doc,
                "source":      meta.get("source", "unknown"),
                "page":        meta.get("page", -1),
                "chunk_index": meta.get("chunk_index", -1),
                "source_type": "competitor",
                "score":       round(1 - float(dist), 4),
            })
        return chunks
    except Exception as exc:
        logger.warning("Competitor chunk retrieval failed: %s", exc)
        return []


def retrieve_layered(query: str) -> StructuredContext:
    """
    Priority-ordered retrieval across all context sources.

    Retrieval order (highest to lowest priority):
      1. Author chunks        (source_type=author,  top_k from config)
      2. Book context text    (fixed ID fetch)
      3. Outline text         (fixed ID fetch)
      4. Competitor chunks    (separate collection, top_k from config)
      5. General chunks       (no source_type filter, excluding special IDs)

    Returns
    -------
    StructuredContext dataclass with each layer populated separately.
    """
    ef = get_embedding_function()
    query_vector: List[float] = ef.embed_query(query)

    # 1. Author
    author_chunks = _retrieve_by_type(query_vector, "author", settings.author_top_k)

    # 2. Book context (direct ID)
    book_context_text = _get_doc_by_id("book_context_active")

    # 3. Outline (direct ID)
    outline_text = _get_doc_by_id("outline_active")

    # 4. Competitor (separate collection)
    competitor_chunks = _retrieve_competitor_chunks(query_vector, settings.competitor_top_k)

    # 5. General — retrieve broadly then strip priority docs
    _special_sources = {"__book_context__", "__chapter_outline__"}
    _priority_types  = {"author", "context", "outline"}
    general_raw = retrieve_chunks(
        query=query,
        top_k=settings.general_top_k + 5,   # over-fetch then trim
    )
    general_chunks = [
        c for c in general_raw
        if c.get("source_type", "general") not in _priority_types
        and c.get("source", "") not in _special_sources
    ][: settings.general_top_k]

    logger.info(
        "retrieve_layered: author=%d bk_ctx=%s outline=%s competitor=%d general=%d",
        len(author_chunks),
        "yes" if book_context_text else "no",
        "yes" if outline_text else "no",
        len(competitor_chunks),
        len(general_chunks),
    )
    return StructuredContext(
        author_chunks=author_chunks,
        book_context_text=book_context_text,
        outline_text=outline_text,
        competitor_chunks=competitor_chunks,
        general_chunks=general_chunks,
    )
