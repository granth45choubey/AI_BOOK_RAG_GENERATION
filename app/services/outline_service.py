"""
Chapter Outline Service.

Persists the chapter outline in two places:
  1. JSON file on disk  — survives server restarts.
  2. Main ChromaDB collection — source_type="outline", priority_score=0.9
     (fixed ID: outline_active, always upserted so only one outline is active).

Pydantic schemas (ChapterSection, Chapter, ChapterOutlineRequest) are defined
here and re-exported by the route module.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.rag_pipeline.embedder import get_embedding_function
from app.rag_pipeline.retriever import get_collection
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
    chapters: List[Chapter]


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


# ── Public API ────────────────────────────────────────────────────────────────

def save_outline(request: ChapterOutlineRequest) -> Dict[str, Any]:
    """
    Persist the chapter outline to disk and into ChromaDB.

    Returns
    -------
    dict with chapters list and formatted outline_text.
    """
    outline_dict = request.model_dump()
    n_chapters = len(request.chapters)

    # 1. Disk persistence
    path = _outline_path()
    path.write_text(
        json.dumps(outline_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Chapter outline saved to %s (%d chapters).", path, n_chapters)

    # 2. Embed + upsert into main collection (fixed ID → always single active outline)
    outline_text = _format_outline_text(request.chapters)
    ef = get_embedding_function()
    vector = ef.embed_documents([outline_text])[0]

    collection = get_collection()
    collection.upsert(
        ids=[_OUTLINE_ID],
        documents=[outline_text],
        embeddings=[vector],
        metadatas=[{
            "doc_type":      "outline",
            "source_type":   "outline",
            "priority_score": 0.9,
            "source":        "__chapter_outline__",
            "page":          0,
            "chunk_index":   0,
        }],
    )
    logger.info("Chapter outline upserted into ChromaDB (%d chapters).", n_chapters)

    return {
        "chapters":     outline_dict["chapters"],
        "outline_text": outline_text,
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

    # Remove from ChromaDB (ignore if not present)
    try:
        collection = get_collection()
        collection.delete(ids=[_OUTLINE_ID])
        logger.info("Chapter outline removed from ChromaDB.")
    except Exception as exc:
        logger.warning("Could not remove outline from ChromaDB: %s", exc)

    return existed
