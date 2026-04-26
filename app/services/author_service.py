"""
Author Knowledge Ingestion Service.

Saves, parses, chunks, embeds, and stores author-specific content
(questionnaires, transcripts, notes) in the main ChromaDB collection
with source_type="author" and priority_score=1.0.

These chunks are retrieved first in the layered retrieval pipeline
and strongly influence the LLM's generation.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List

from app.rag_pipeline.chunker import chunk_documents
from app.rag_pipeline.retriever import store_chunks_with_type
from app.utils.config import get_settings
from app.utils.file_parser import parse_file

logger = logging.getLogger(__name__)
settings = get_settings()


def ingest_author_documents_sync(file_data: List[Dict]) -> dict:
    """
    Core ingestion pipeline for author-specific documents — fully synchronous,
    safe for a ThreadPoolExecutor.

    Parameters
    ----------
    file_data : list of {filename: str, content: bytes}

    Returns
    -------
    Summary dict: {total_files, total_chunks_stored, details}
    """
    os.makedirs(settings.author_upload_dir, exist_ok=True)

    results = []
    total_chunks = 0

    for item in file_data:
        filename: str = item["filename"]
        content: bytes = item["content"]

        ext = Path(filename).suffix.lower()
        if ext not in settings.allowed_extensions:
            results.append({
                "filename": filename,
                "status": "skipped",
                "reason": f"Unsupported file type: {ext}",
            })
            continue

        # ── Save ─────────────────────────────────────────────────────────────
        save_path = os.path.join(settings.author_upload_dir, filename)
        try:
            with open(save_path, "wb") as fh:
                fh.write(content)
        except Exception as exc:
            logger.error("Could not save author file '%s': %s", filename, exc)
            results.append({"filename": filename, "status": "error", "reason": str(exc)})
            continue

        # ── Parse ─────────────────────────────────────────────────────────────
        try:
            pages = parse_file(save_path)
        except Exception as exc:
            logger.error("Parse failed for '%s': %s", filename, exc)
            results.append({"filename": filename, "status": "error",
                            "reason": f"Parse error: {exc}"})
            continue

        logger.info("Parsed author doc '%s' → %d pages", filename, len(pages))

        # ── Chunk ─────────────────────────────────────────────────────────────
        chunks = chunk_documents(pages)
        logger.info("Chunked author doc '%s' → %d chunks", filename, len(chunks))

        # ── Embed + store with author priority ────────────────────────────────
        try:
            n_stored = store_chunks_with_type(
                chunks,
                source_type="author",
                priority_score=1.0,
            )
            total_chunks += n_stored
            results.append({
                "filename": filename,
                "status": "success",
                "pages": len(pages),
                "chunks_stored": n_stored,
                "source_type": "author",
                "priority": "HIGH",
            })
            logger.info("Stored %d author chunks for '%s'", n_stored, filename)
        except Exception as exc:
            logger.error("Storage failed for '%s': %s", filename, exc)
            results.append({"filename": filename, "status": "error",
                            "reason": f"Storage error: {exc}"})

    return {
        "total_files": len(file_data),
        "total_chunks_stored": total_chunks,
        "source_type": "author",
        "details": results,
    }
