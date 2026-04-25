"""
Query service.

Orchestrates: embed query → retrieve chunks → filter by score → inject book
context (if set) → generate answer.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any

from app.rag_pipeline.retriever import retrieve_chunks
from app.rag_pipeline.generator import generate_answer
from app.services.book_context_service import get_active_book_context
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Minimum cosine-similarity score to consider a chunk relevant.
# Chunks below this threshold are dropped before going to the LLM.
MIN_SCORE: float = 0.10
# Fallback: always pass at least this many chunks even if all are below threshold
FALLBACK_TOP_N: int = 3


def answer_query(
    question: str,
    top_k: int | None = None,
    source_filter: str | None = None,
) -> Dict[str, Any]:
    """
    Full RAG query pipeline.

    Parameters
    ----------
    question : user's question
    top_k : number of context chunks to retrieve
    source_filter : restrict to a specific source filename (optional)

    Returns
    -------
    dict with answer, sources, and retrieved chunks
    """
    top_k = top_k or settings.retrieval_top_k
    filter_meta = {"source": source_filter} if source_filter else None

    # ── Retrieve ─────────────────────────────────────────────────────────────
    chunks = retrieve_chunks(query=question, top_k=top_k, filter_metadata=filter_meta)

    # ── Filter by relevance score ─────────────────────────────────────────────
    if chunks:
        good_chunks = [c for c in chunks if c["score"] >= MIN_SCORE]
        if good_chunks:
            chunks = good_chunks
        else:
            # All chunks are low-quality — still pass the best ones so the LLM
            # can attempt an answer rather than failing silently.
            logger.warning(
                "All %d retrieved chunks scored below %.2f — using top-%d as fallback.",
                len(chunks), MIN_SCORE, FALLBACK_TOP_N,
            )
            chunks = chunks[:FALLBACK_TOP_N]

    logger.info(
        "Passing %d chunks to LLM for question: %.60s…", len(chunks), question
    )

    # ── Fetch active book context (if set) ──────────────────────────────────
    book_context = get_active_book_context()
    if book_context:
        logger.info("Book context active — injecting into prompt.")

    # ── Generate ───────────────────────────────────────────────────────────────
    answer = generate_answer(question, chunks, book_context=book_context)

    # ── Build source citations ────────────────────────────────────────────────
    seen: set = set()
    sources: List[Dict[str, Any]] = []
    for c in chunks:
        key = (c["source"], c["page"])
        if key not in seen:
            seen.add(key)
            sources.append({"source": c["source"], "page": c["page"]})

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": chunks,
    }
