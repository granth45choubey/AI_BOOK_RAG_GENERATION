"""
Query service — updated with layered retrieval path.

Pipeline selection:
  - If layered book/market context is present → structured generation
    (generate_answer_structured with priority-ordered StructuredContext)
  - If source_filter is set → flat retrieval (filename filter not supported
    by the layered path)
  - Otherwise → flat retrieval + generate_answer (backward compat)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.rag_pipeline.generator import generate_answer, generate_answer_structured
from app.rag_pipeline.retriever import retrieve_chunks, retrieve_layered
from app.services.book_context_service import get_active_book_context
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MIN_SCORE:      float = 0.10
FALLBACK_TOP_N: int   = 3


def _use_structured_path(ctx) -> bool:
    """True when layered context should drive structured generation."""
    return bool(
        ctx.author_chunks
        or ctx.book_context_text
        or ctx.outline_text
        or ctx.research_chunks
        or ctx.industry_chunks
        or ctx.whitepaper_chunks
        or ctx.competitor_chunks
    )


def _collect_structured_chunks(ctx) -> List[Dict[str, Any]]:
    """Merge all layered chunk lists for citations (dedup handled downstream)."""
    return (
        ctx.author_chunks
        + ctx.research_chunks
        + ctx.industry_chunks
        + ctx.whitepaper_chunks
        + ctx.competitor_chunks
        + ctx.general_chunks
    )


def answer_query(
    question: str,
    top_k: Optional[int] = None,
    source_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full RAG query pipeline.

    Uses the layered (priority-ordered) retrieval path when priority content
    (author docs / book context / outline) is available; falls back to the
    original flat retrieval otherwise to maintain backward compatibility.

    Parameters
    ----------
    question      : user's question / writing task
    top_k         : number of general chunks to retrieve (used in fallback path)
    source_filter : restrict retrieval to a specific source filename (fallback path)

    Returns
    -------
    dict: {question, answer, sources, retrieved_chunks}
    """
    # ── Layered retrieval ─────────────────────────────────────────────────────
    ctx = retrieve_layered(question)

    use_structured = _use_structured_path(ctx) and not source_filter

    if use_structured:
        # ── Structured generation (enhanced path) ─────────────────────────────
        logger.info(
            "Using structured generation path "
            "(author=%d, ctx=%s, outline=%s, research=%d, industry=%d, "
            "whitepaper=%d, competitor=%d, general=%d).",
            len(ctx.author_chunks),
            "yes" if ctx.book_context_text else "no",
            "yes" if ctx.outline_text else "no",
            len(ctx.research_chunks),
            len(ctx.industry_chunks),
            len(ctx.whitepaper_chunks),
            len(ctx.competitor_chunks),
            len(ctx.general_chunks),
        )
        answer     = generate_answer_structured(question, ctx)
        all_chunks = _collect_structured_chunks(ctx)

    else:
        # ── Fallback: original flat retrieval (backward compat) ───────────────
        logger.info("No priority context found — using flat retrieval (backward compat).")
        top_k       = top_k or settings.retrieval_top_k
        filter_meta = {"source": source_filter} if source_filter else None

        chunks = retrieve_chunks(query=question, top_k=top_k, filter_metadata=filter_meta)

        if chunks:
            good = [c for c in chunks if c["score"] >= MIN_SCORE]
            chunks = good if good else chunks[:FALLBACK_TOP_N]
            if not good:
                logger.warning(
                    "All %d chunks scored below %.2f — using top-%d as fallback.",
                    len(chunks), MIN_SCORE, FALLBACK_TOP_N,
                )

        book_context = get_active_book_context()
        if book_context:
            logger.info("Book context active — injecting into flat prompt.")

        answer     = generate_answer(question, chunks, book_context=book_context)
        all_chunks = chunks

    # ── Build deduplicated source citations ───────────────────────────────────
    seen:    set              = set()
    sources: List[Dict[str, Any]] = []
    for c in all_chunks:
        key = (c.get("source", ""), c.get("page", 0))
        if key not in seen:
            seen.add(key)
            sources.append({"source": c.get("source", ""), "page": c.get("page", 0)})

    return {
        "question":         question,
        "answer":           answer,
        "sources":          sources,
        "retrieved_chunks": all_chunks,
    }
