"""
Document ingestion service.

Orchestrates: file save → parse → chunk → embed → store

Two entry points:
  ingest_documents_sync(file_data)  — pure-sync, safe to run in a thread pool.
  ingest_documents(files)           — async wrapper kept for backward compat.
"""
from __future__ import annotations

import os
import logging
import time
from pathlib import Path
from typing import List, Dict

from app.utils.config import get_settings
from app.utils.file_parser import parse_file
from app.rag_pipeline.chunker import chunk_documents
from app.rag_pipeline.retriever import store_chunks

logger = logging.getLogger(__name__)
settings = get_settings()


def ingest_documents_sync(file_data: List[Dict]) -> dict:
    """
    Core ingestion logic — **fully synchronous**, safe for a ThreadPoolExecutor.

    Parameters
    ----------
    file_data : list of dicts with keys:
        - filename : str   — original filename (used for extension check & save path)
        - content  : bytes — raw file bytes already read from the upload

    Returns
    -------
    Summary dict: {total_files, total_chunks_stored, details}
    """
    os.makedirs(settings.upload_dir, exist_ok=True)

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

        # ── Save file ────────────────────────────────────────────────────────
        t_file_start = time.perf_counter()
        save_path = os.path.join(settings.upload_dir, filename)
        try:
            with open(save_path, "wb") as f:
                f.write(content)
        except Exception as exc:
            logger.error("Failed to save '%s': %s", filename, exc)
            results.append({"filename": filename, "status": "error", "reason": str(exc)})
            continue
        t_save = time.perf_counter() - t_file_start

        # ── Parse ────────────────────────────────────────────────────────────
        t_parse_start = time.perf_counter()
        try:
            pages = parse_file(save_path)
        except Exception as exc:
            logger.error("Failed to parse '%s': %s", filename, exc)
            results.append({"filename": filename, "status": "error", "reason": f"Parse error: {exc}"})
            continue
        t_parse = time.perf_counter() - t_parse_start

        logger.info("Parsed '%s' → %d pages (%.2fs)", filename, len(pages), t_parse)

        # ── Chunk ────────────────────────────────────────────────────────────
        t_chunk_start = time.perf_counter()
        chunks = chunk_documents(pages)
        t_chunk = time.perf_counter() - t_chunk_start
        logger.info("Chunked '%s' → %d chunks (%.2fs)", filename, len(chunks), t_chunk)

        # ── Embed + Store ────────────────────────────────────────────────────
        t_embed_start = time.perf_counter()
        try:
            n_stored = store_chunks(chunks)
            t_embed = time.perf_counter() - t_embed_start
            total_chunks += n_stored
            results.append({
                "filename": filename,
                "status": "success",
                "pages": len(pages),
                "chunks_stored": n_stored,
                "timing_seconds": {
                    "save": round(t_save, 3),
                    "parse": round(t_parse, 3),
                    "chunk": round(t_chunk, 3),
                    "embed_and_store": round(t_embed, 3),
                    "total": round(t_save + t_parse + t_chunk + t_embed, 3),
                },
            })
            logger.info(
                "Stored %d chunks for '%s' in %.2fs (embed+store=%.2fs)",
                n_stored, filename, t_save + t_parse + t_chunk + t_embed, t_embed,
            )
        except Exception as exc:
            logger.error("Failed to store chunks for '%s': %s", filename, exc)
            results.append({"filename": filename, "status": "error", "reason": f"Storage error: {exc}"})

    return {
        "total_files": len(file_data),
        "total_chunks_stored": total_chunks,
        "details": results,
    }


# ── Async convenience wrapper (kept for backward compatibility) ───────────────

async def ingest_documents(files) -> dict:
    """
    Async wrapper — reads file bytes then delegates to ingest_documents_sync.

    Prefer calling ingest_documents_sync directly inside a thread-pool executor
    (as the upload route now does) to avoid blocking the event loop.
    """
    file_data = []
    for f in files:
        content = await f.read()
        file_data.append({"filename": f.filename, "content": content})
    return ingest_documents_sync(file_data)

