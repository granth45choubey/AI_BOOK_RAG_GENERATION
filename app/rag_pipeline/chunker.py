"""
Text chunking module.

Strategies
----------
- "recursive"  → LangChain RecursiveCharacterTextSplitter (default, fast)
- "semantic"   → Splits on sentence boundaries with rolling window merge
                 (no heavy ML dependency required)

Each chunk dict carries full metadata so ChromaDB can filter / display it.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def chunk_documents(
    pages: List[Dict[str, Any]],
    strategy: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[Dict[str, Any]]:
    """
    Split a list of page dicts into smaller chunks.

    Parameters
    ----------
    pages : list of dicts with keys: text, source, page
    strategy : "recursive" | "semantic" (falls back to settings)
    chunk_size : characters per chunk (falls back to settings)
    chunk_overlap : character overlap (falls back to settings)

    Returns
    -------
    list of dicts: {text, source, page, chunk_index}
    """
    strategy = strategy or settings.chunk_strategy
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    if strategy == "recursive":
        return _recursive_chunk(pages, chunk_size, chunk_overlap)
    elif strategy == "semantic":
        return _semantic_chunk(pages, chunk_size, chunk_overlap)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy!r}")


# ── Recursive splitter ────────────────────────────────────────────────────────

def _recursive_chunk(
    pages: List[Dict[str, Any]],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Dict[str, Any]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    for page in pages:
        texts = splitter.split_text(page["text"])
        for t in texts:
            if t.strip():
                chunks.append({
                    "text": t.strip(),
                    "source": page["source"],
                    "page": page["page"],
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

    logger.info("Recursive chunking → %d chunks from %d pages", len(chunks), len(pages))
    return chunks


# ── Semantic splitter (sentence-aware rolling window) ─────────────────────────

def _semantic_chunk(
    pages: List[Dict[str, Any]],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Dict[str, Any]]:
    """
    Lightweight semantic chunker that splits on sentence boundaries
    and merges them into windows of ~chunk_size characters.
    """
    import re

    _sentence_end = re.compile(r'(?<=[.!?])\s+')

    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    for page in pages:
        sentences = _sentence_end.split(page["text"])
        sentences = [s.strip() for s in sentences if s.strip()]

        current: List[str] = []
        current_len = 0

        for sent in sentences:
            sent_len = len(sent)
            if current_len + sent_len > chunk_size and current:
                # Emit current window
                chunk_text = " ".join(current)
                chunks.append({
                    "text": chunk_text,
                    "source": page["source"],
                    "page": page["page"],
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

                # Carry-over overlap sentences
                carry = []
                carry_len = 0
                for s in reversed(current):
                    if carry_len + len(s) <= chunk_overlap:
                        carry.insert(0, s)
                        carry_len += len(s)
                    else:
                        break
                current = carry
                current_len = carry_len

            current.append(sent)
            current_len += sent_len

        if current:
            chunks.append({
                "text": " ".join(current),
                "source": page["source"],
                "page": page["page"],
                "chunk_index": chunk_index,
            })
            chunk_index += 1

    logger.info("Semantic chunking → %d chunks from %d pages", len(chunks), len(pages))
    return chunks
