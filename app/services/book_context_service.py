"""
Book Context Service.

Responsibilities
----------------
- Accept structured book metadata and persist it in ChromaDB with a special
  ``doc_type: book_context`` metadata flag so it can always be fetched first.
- Expose helpers to retrieve the active book context for prompt injection.

Design note
-----------
Book context is stored as a *single* document under the fixed ID
``book_context_active`` so that creating a new context always overwrites the
previous one (upsert semantics).  If you want a history of contexts, remove
the fixed ID and use UUIDs instead.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.rag_pipeline.embedder import get_embedding_function
from app.rag_pipeline.retriever import get_collection
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Fixed Chroma document ID so a new creation always replaces the old one.
_BOOK_CTX_ID = "book_context_active"
_DOC_TYPE_TAG = "book_context"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_context_text(data: dict) -> str:
    """
    Render the structured book metadata into a rich, human-readable paragraph
    that the LLM can understand as high-level authoring intent.
    """
    lines = [
        f"Book Title: {data['title']}",
    ]
    if data.get("subtitle"):
        lines.append(f"Subtitle: {data['subtitle']}")
    lines += [
        f"Target Audience: {data['target_audience']}",
        f"Author's Objective: {data['author_objective']}",
        f"Reader Transformation: {data['reader_transformation']}",
        f"Reader's Initial State (before reading): {data['initial_state']}",
        f"Reader's Final State (after reading): {data['final_state']}",
        f"Tone & Style: {data['tone']}",
    ]
    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def create_book_context(
    title: str,
    subtitle: str,
    target_audience: str,
    author_objective: str,
    reader_transformation: str,
    initial_state: str,
    final_state: str,
    tone: str,
) -> dict:
    """
    Persist book context into ChromaDB as a high-priority document.

    The document is upserted under the fixed ID ``book_context_active`` so
    successive calls simply update the context.

    Returns the stored context dict.
    """
    data = {
        "title": title,
        "subtitle": subtitle,
        "target_audience": target_audience,
        "author_objective": author_objective,
        "reader_transformation": reader_transformation,
        "initial_state": initial_state,
        "final_state": final_state,
        "tone": tone,
    }

    context_text = _build_context_text(data)

    ef = get_embedding_function()
    vector = ef.embed_documents([context_text])[0]

    collection = get_collection()
    collection.upsert(
        ids=[_BOOK_CTX_ID],
        documents=[context_text],
        embeddings=[vector],
        metadatas=[{
            "doc_type": _DOC_TYPE_TAG,
            "source": "__book_context__",
            "page": 0,
            "chunk_index": 0,
            # Store JSON blob so we can reconstruct the full struct later
            "raw_json": json.dumps(data),
        }],
    )

    logger.info("Book context stored: '%s'", title)
    return {"context_text": context_text, **data}


def get_active_book_context() -> Optional[str]:
    """
    Fetch the active book context text from ChromaDB.

    Returns the context string, or ``None`` if no context has been set yet.
    """
    collection = get_collection()

    try:
        result = collection.get(
            ids=[_BOOK_CTX_ID],
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        logger.warning("Could not fetch book context: %s", exc)
        return None

    docs = result.get("documents") or []
    if not docs or not docs[0]:
        return None

    return docs[0]


def get_active_book_context_struct() -> Optional[dict]:
    """
    Fetch the full structured book context from ChromaDB.

    Returns a dict with all book fields, or ``None`` if none is set.
    """
    collection = get_collection()

    try:
        result = collection.get(
            ids=[_BOOK_CTX_ID],
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        logger.warning("Could not fetch book context struct: %s", exc)
        return None

    metas = result.get("metadatas") or []
    if not metas or not metas[0]:
        return None

    raw = metas[0].get("raw_json")
    if not raw:
        return None

    try:
        return json.loads(raw)
    except Exception:
        return None
