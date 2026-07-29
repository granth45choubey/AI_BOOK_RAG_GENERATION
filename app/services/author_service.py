"""
Author Knowledge Ingestion Service — v2.

Saves, parses, chunks, embeds, and stores author-specific content
(questionnaires, transcripts, notes) in the main ChromaDB collection
with source_type="author" and priority_score=1.0.

NEW: Accepts an optional `description` string per upload batch.
Descriptions are:
  - Stored in chunk metadata as `author_description`.
  - Aggregated in a JSON sidecar file (author_docs/descriptions.json).
  - Injected into the generation prompt as "Author Guidance".
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.rag_pipeline.chunker import chunk_documents
from app.rag_pipeline.retriever import store_chunks_with_type
from app.utils.config import get_settings
from app.utils.file_parser import parse_file

logger = logging.getLogger(__name__)
settings = get_settings()

_DESCRIPTIONS_FILE = Path(settings.author_upload_dir) / "descriptions.json"


# ── Description persistence ────────────────────────────────────────────────────

def _load_descriptions() -> List[Dict]:
    if _DESCRIPTIONS_FILE.exists():
        try:
            return json.loads(_DESCRIPTIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_descriptions(entries: List[Dict]) -> None:
    _DESCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DESCRIPTIONS_FILE.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def save_author_description(description: str, filenames: List[str]) -> None:
    """Append a description entry for this upload batch."""
    entries = _load_descriptions()
    entries.append({
        "description":  description,
        "filenames":    filenames,
        "timestamp":    datetime.now(tz=timezone.utc).isoformat(),
    })
    _save_descriptions(entries)
    logger.info("Author description saved for files: %s", filenames)


def get_aggregated_author_descriptions() -> str:
    """
    Return all stored author descriptions as a single formatted string.
    Returns empty string if none exist.
    """
    entries = _load_descriptions()
    if not entries:
        return ""
    parts = []
    for e in entries:
        files_str = ", ".join(e.get("filenames", []))
        ts = e.get("timestamp", "")[:10]  # date only
        parts.append(
            f"[{ts} — {files_str}]\n{e['description']}"
        )
    return "\n\n".join(parts)


def clear_author_descriptions() -> None:
    """Remove the descriptions sidecar (used during reset operations)."""
    _DESCRIPTIONS_FILE.unlink(missing_ok=True)


# ── Core ingestion ─────────────────────────────────────────────────────────────

def ingest_author_documents_sync(
    file_data: List[Dict],
    description: Optional[str] = None,
) -> dict:
    """
    Core ingestion pipeline for author-specific documents — fully synchronous,
    safe for a ThreadPoolExecutor.

    Parameters
    ----------
    file_data   : list of {filename: str, content: bytes}
    description : optional author guidance string for this batch

    Returns
    -------
    Summary dict: {total_files, total_chunks_stored, details}
    """
    os.makedirs(settings.author_upload_dir, exist_ok=True)

    results = []
    total_chunks = 0
    successful_files: List[str] = []

    for item in file_data:
        filename: str = item["filename"]
        content: bytes = item["content"]

        ext = Path(filename).suffix.lower()
        if ext not in settings.allowed_extensions:
            results.append({
                "filename": filename,
                "status":   "skipped",
                "reason":   f"Unsupported file type: {ext}",
            })
            continue

        # ── Save ──────────────────────────────────────────────────────────────
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

        # ── Embed + store with author priority + description metadata ─────────
        try:
            n_stored = store_chunks_with_type(
                chunks,
                source_type="author",
                priority_score=1.0,
                extra_metadata={"author_description": description or ""},
            )
            total_chunks += n_stored
            successful_files.append(filename)
            results.append({
                "filename":    filename,
                "status":      "success",
                "pages":       len(pages),
                "chunks_stored": n_stored,
                "source_type": "author",
                "priority":    "HIGH",
                "description_attached": bool(description),
            })
            logger.info("Stored %d author chunks for '%s'", n_stored, filename)
        except Exception as exc:
            logger.error("Storage failed for '%s': %s", filename, exc)
            results.append({"filename": filename, "status": "error",
                            "reason": f"Storage error: {exc}"})

    # ── Persist description if any files were stored successfully ──────────────
    if description and description.strip() and successful_files:
        save_author_description(description.strip(), successful_files)

    return {
        "total_files":         len(file_data),
        "total_chunks_stored": total_chunks,
        "source_type":         "author",
        "description_saved":   bool(description and successful_files),
        "details":             results,
    }
