"""
Chapter Outline Service.

Persists the chapter outline in two places:
  1. JSON file on disk  — survives server restarts.
  2. Main ChromaDB collection — source_type="outline", priority_score=0.9
     (fixed ID: outline_active, always upserted so only one outline is active).

Pydantic schemas
----------------
  ChapterSection         — a single section within a chapter
  Chapter                — a chapter with its sections
  ChapterOutlineRequest  — legacy JSON input (chapters list)  [backward-compat]
  OutlineTextRequest     — NEW: plain-text outline input

Public API
----------
  save_outline(request)              — legacy JSON-based save
  save_outline_from_text(text)       — NEW: text → parse → save
  get_active_outline()               — load from disk (None if unset)
  get_outline_text()                 — formatted string for prompt injection
  delete_outline()                   — remove from disk + ChromaDB
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator

from app.rag_pipeline.embedder import embed_documents
from app.rag_pipeline.retriever import get_collection
from app.services.outline_parser import outline_text_to_request_dict
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_OUTLINE_ID = "outline_active"


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ChapterSection(BaseModel):
    title: str
    description: Optional[str] = None


class Chapter(BaseModel):
    title: str
    sections: List[ChapterSection] = []


class ChapterOutlineRequest(BaseModel):
    """Legacy schema — accepts a structured chapters list (backward-compatible)."""
    chapters: List[Chapter]


class OutlineTextRequest(BaseModel):
    """New schema — accepts free-form plain-text outline."""
    outline_text: str

    @field_validator("outline_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("outline_text must not be blank.")
        return v.strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _outline_path() -> Path:
    p = Path(settings.outline_store_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _format_outline_text(chapters: List[Chapter]) -> str:
    """Render the outline as a readable string suitable for embedding."""
    lines = ["# Chapter Outline\n"]
    for i, ch in enumerate(chapters, 1):
        lines.append(f"## Chapter {i}: {ch.title}")
        for j, sec in enumerate(ch.sections, 1):
            desc = f" — {sec.description}" if sec.description else ""
            lines.append(f"  {i}.{j}. {sec.title}{desc}")
        lines.append("")
    return "\n".join(lines)


def _upsert_to_chromadb(outline_text: str) -> None:
    """Embed and upsert the formatted outline string into ChromaDB."""
    vector = embed_documents([outline_text])[0]
    collection = get_collection()
    collection.upsert(
        ids=[_OUTLINE_ID],
        documents=[outline_text],
        embeddings=[vector],
        metadatas=[{
            "doc_type":       "outline",
            "source_type":    "outline",
            "priority_score": 0.9,
            "source":         "__chapter_outline__",
            "page":           0,
            "chunk_index":    0,
        }],
    )
    logger.info("Chapter outline upserted into ChromaDB.")


# ── Public API ────────────────────────────────────────────────────────────────

def save_outline_from_text(outline_text: str) -> Dict[str, Any]:
    """
    Parse plain-text outline, validate it, then persist to disk and ChromaDB.

    Parameters
    ----------
    outline_text : raw author-supplied text

    Returns
    -------
    {
      "chapters":       [...],
      "chapters_count": int,
      "outline_text":   str,   # formatted version stored in ChromaDB
      "original_text":  str,   # author's original input
      "warnings":       [...]  # parse/validation warnings (non-fatal)
    }

    Raises
    ------
    ValueError  if the text produces zero chapters (hard validation failure).
    """
    parsed = outline_text_to_request_dict(outline_text)
    chapters_raw: List[Dict[str, Any]] = parsed["chapters"]
    warnings: List[str] = parsed["warnings"]
    original_text: str = parsed["original_text"]

    # Hard failure: no chapters detected
    hard_errors = [w for w in warnings if not w.startswith("⚠")]
    if not chapters_raw or hard_errors:
        raise ValueError(
            hard_errors[0]
            if hard_errors
            else "No chapters could be parsed from the provided text."
        )

    # Build Chapter objects from parsed dicts
    chapter_objs = [
        Chapter(
            title=ch["title"],
            sections=[
                ChapterSection(
                    title=sec["title"],
                    description=sec.get("description"),
                )
                for sec in ch.get("sections", [])
            ],
        )
        for ch in chapters_raw
    ]

    # Disk persistence (includes original_text + metadata)
    path = _outline_path()
    disk_payload = {
        "chapters": [ch.model_dump() for ch in chapter_objs],
        "original_text": original_text,
        "metadata": {
            "source_type": "outline",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    path.write_text(json.dumps(disk_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Chapter outline saved to %s (%d chapters).", path, len(chapter_objs)
    )

    # ChromaDB
    formatted_text = _format_outline_text(chapter_objs)
    _upsert_to_chromadb(formatted_text)

    return {
        "chapters":       [ch.model_dump() for ch in chapter_objs],
        "chapters_count": len(chapter_objs),
        "outline_text":   formatted_text,
        "original_text":  original_text,
        "warnings":       [w for w in warnings if w.startswith("⚠")],  # soft-only
    }


def save_outline(request: ChapterOutlineRequest) -> Dict[str, Any]:
    """
    Persist the chapter outline from a structured request (legacy JSON path).

    Returns
    -------
    dict with chapters list and formatted outline_text.
    """
    outline_dict = request.model_dump()
    n_chapters = len(request.chapters)

    # Disk persistence
    path = _outline_path()
    disk_payload = {
        "chapters": outline_dict["chapters"],
        "original_text": None,   # no raw text for legacy JSON input
        "metadata": {
            "source_type": "outline",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    path.write_text(
        json.dumps(disk_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Chapter outline saved to %s (%d chapters).", path, n_chapters)

    # ChromaDB
    outline_text = _format_outline_text(request.chapters)
    _upsert_to_chromadb(outline_text)

    return {
        "chapters":       outline_dict["chapters"],
        "outline_text":   outline_text,
        "chapters_count": n_chapters,
    }


def get_active_outline() -> Optional[Dict[str, Any]]:
    """Load the current outline from disk. Returns None if not set."""
    path = _outline_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read outline file: %s", exc)
        return None


def get_outline_text() -> Optional[str]:
    """Return the formatted outline string, or None if no outline is set."""
    outline = get_active_outline()
    if not outline:
        return None
    chapters = [Chapter(**ch) for ch in outline.get("chapters", [])]
    return _format_outline_text(chapters)


def delete_outline() -> bool:
    """
    Remove the active chapter outline from disk and from ChromaDB.
    Returns True if an outline existed and was removed, False otherwise.
    """
    path = _outline_path()
    existed = path.exists()
    if existed:
        path.unlink()
        logger.info("Chapter outline file deleted.")

    try:
        collection = get_collection()
        collection.delete(ids=[_OUTLINE_ID])
        logger.info("Chapter outline removed from ChromaDB.")
    except Exception as exc:
        logger.warning("Could not remove outline from ChromaDB: %s", exc)

    return existed
