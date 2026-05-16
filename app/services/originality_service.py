"""
Originality check service.

Uses embeddings to find similar passages in competitor and general collections.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.rag_pipeline.embedder import get_embedding_function
from app.rag_pipeline.retriever import get_collection
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _query_collection(collection, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
    count = collection.count()
    if count == 0:
        return []
    n = min(top_k, count)
    res = collection.query(
        query_embeddings=[query_vector],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    matches: List[Dict[str, Any]] = []
    for doc, meta, dist in zip(
        res["documents"][0],
        res["metadatas"][0],
        res["distances"][0],
    ):
        matches.append({
            "text": doc,
            "source": meta.get("source", "unknown") if meta else "unknown",
            "page": meta.get("page", -1) if meta else -1,
            "source_type": meta.get("source_type", "general") if meta else "general",
            "score": round(1 - float(dist), 4),
        })
    return matches


def _competitor_collection():
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=settings.competitor_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def check_originality(
    text: str,
    top_k: Optional[int] = None,
    threshold: Optional[float] = None,
    include_competitor: bool = True,
    include_general: bool = True,
) -> Dict[str, Any]:
    """
    Compare input text against stored corpora and return similarity matches.

    Returns a dict with matches, max_score, and flagged status.
    """
    if not text.strip():
        return {"matches": [], "max_score": 0.0, "flagged": False}

    top_k = top_k or settings.originality_top_k
    threshold = threshold if threshold is not None else settings.originality_threshold

    ef = get_embedding_function()
    query_vector = ef.embed_query(text)

    matches: List[Dict[str, Any]] = []

    if include_general:
        general_matches = _query_collection(get_collection(), query_vector, top_k)
        for m in general_matches:
            m["collection"] = "general"
        matches.extend(general_matches)

    if include_competitor:
        comp_matches = _query_collection(_competitor_collection(), query_vector, top_k)
        for m in comp_matches:
            m["collection"] = "competitor"
        matches.extend(comp_matches)

    matches.sort(key=lambda m: m.get("score", 0.0), reverse=True)
    max_score = matches[0]["score"] if matches else 0.0
    flagged = max_score >= float(threshold)

    logger.info(
        "Originality check: top_k=%d threshold=%.2f max_score=%.4f flagged=%s",
        top_k,
        float(threshold),
        max_score,
        "yes" if flagged else "no",
    )

    return {
        "matches": matches,
        "max_score": max_score,
        "flagged": flagged,
        "threshold": float(threshold),
    }
