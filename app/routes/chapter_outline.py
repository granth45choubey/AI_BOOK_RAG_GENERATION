"""
POST /set-chapter-outline   — save or replace the active chapter outline
GET  /set-chapter-outline   — retrieve the current outline (or 404 if none)
DELETE /set-chapter-outline — remove the outline
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.services.outline_service import (
    Chapter,
    ChapterOutlineRequest,
    ChapterSection,
    delete_outline,
    get_active_outline,
    save_outline,
)

router = APIRouter(prefix="/set-chapter-outline", tags=["Chapter Outline"])


# ── Request/Response schemas (re-exported from outline_service) ───────────────
# ChapterSection, Chapter, ChapterOutlineRequest are defined in outline_service
# and imported here so Swagger docs pick them up automatically.

__all__ = ["ChapterSection", "Chapter", "ChapterOutlineRequest"]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    summary="Save or replace the active chapter outline",
    status_code=status.HTTP_201_CREATED,
)
def set_chapter_outline(body: ChapterOutlineRequest):
    """
    Persist the provided chapter outline.

    - Saved to disk (survives server restarts).
    - Also upserted into the main ChromaDB collection as `source_type=outline`.
    - If an outline already exists it is **replaced** (single active outline).
    - The outline is injected into every subsequent RAG generation prompt.

    When an outline is active the LLM is instructed to **follow it strictly**
    and not alter the chapter structure.
    """
    if not body.chapters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chapters list must not be empty.",
        )

    try:
        result = save_outline(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save chapter outline: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message":        f"Chapter outline saved ({result['chapters_count']} chapters).",
            "chapters_count": result["chapters_count"],
            "chapters":       result["chapters"],
            "outline_text":   result["outline_text"],
        },
    )


@router.get(
    "",
    summary="Retrieve the active chapter outline",
)
def get_chapter_outline():
    """
    Return the currently active chapter outline, or 404 if none has been set.
    """
    outline = get_active_outline()
    if outline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chapter outline has been set. POST to /set-chapter-outline first.",
        )
    return {"active": True, **outline}


@router.delete(
    "",
    summary="Delete the active chapter outline",
    status_code=status.HTTP_200_OK,
)
def delete_chapter_outline():
    """
    Remove the currently active chapter outline from disk and ChromaDB.
    Subsequent RAG queries will generate the outline dynamically.
    """
    existed = delete_outline()
    if not existed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chapter outline is currently active.",
        )
    return {"message": "Chapter outline cleared successfully.", "active": False}
