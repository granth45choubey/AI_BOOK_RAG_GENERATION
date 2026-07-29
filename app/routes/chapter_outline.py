"""
Chapter Outline Routes.

POST   /set-chapter-outline          — save/replace outline from plain text
POST   /set-chapter-outline/json     — save/replace outline from JSON (legacy)
GET    /set-chapter-outline          — retrieve current outline (404 if none)
DELETE /set-chapter-outline          — remove outline
POST   /set-chapter-outline/preview  — parse text and return preview (no save)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.services.outline_parser import outline_text_to_request_dict
from app.services.outline_service import (
    Chapter,
    ChapterOutlineRequest,
    ChapterSection,
    OutlineTextRequest,
    delete_outline,
    get_active_outline,
    save_outline,
    save_outline_from_text,
)

router = APIRouter(prefix="/set-chapter-outline", tags=["Chapter Outline"])

__all__ = ["ChapterSection", "Chapter", "ChapterOutlineRequest", "OutlineTextRequest"]


# ── POST /set-chapter-outline  (primary — plain text) ────────────────────────

@router.post(
    "",
    summary="Save or replace the active chapter outline (plain text input)",
    status_code=status.HTTP_201_CREATED,
)
def set_chapter_outline_from_text(body: OutlineTextRequest):
    """
    Parse free-form plain-text outline and persist it.

    Accepted formats
    ----------------
    **Format A** — explicit chapter prefix::

        Chapter 1: Why You Can't Focus
        * The myth of laziness
        * Digital distractions

    **Format B** — numbered list::

        1. Why You Can't Focus
           * The myth of laziness
        2. Understanding Attention
           * Deep work

    **Format C** — bare headings + bullets::

        Why You Can't Focus
        • The myth of laziness
        • Digital distractions

    Behaviour
    ---------
    - Persisted to disk (survives restarts).
    - Upserted into ChromaDB as `source_type=outline`.
    - Replaces any previously active outline (single active outline).
    - The LLM strictly follows chapter/section order in every generation.
    - Duplicate chapter titles are automatically removed.
    - Empty section lists are allowed (soft warning only).
    """
    try:
        result = save_outline_from_text(body.outline_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
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
            "original_text":  result["original_text"],
            "warnings":       result.get("warnings", []),
        },
    )


# ── POST /set-chapter-outline/json  (legacy — structured JSON) ────────────────

@router.post(
    "/json",
    summary="Save or replace the active chapter outline (legacy JSON input)",
    status_code=status.HTTP_201_CREATED,
)
def set_chapter_outline_json(body: ChapterOutlineRequest):
    """
    Persist a chapter outline supplied as a structured JSON chapters list.

    This endpoint is kept for backward compatibility.
    Prefer `POST /set-chapter-outline` with `outline_text` for new integrations.
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


# ── POST /set-chapter-outline/preview  (parse without saving) ────────────────

@router.post(
    "/preview",
    summary="Parse outline text and return structured preview (does not save)",
    status_code=status.HTTP_200_OK,
)
def preview_chapter_outline(body: OutlineTextRequest):
    """
    Parse the provided `outline_text` and return the structured hierarchy
    **without persisting** anything.

    Use this to show users a preview before they commit to saving.

    Returns
    -------
    {
      "chapters":      [...],
      "chapters_count": int,
      "warnings":      [...]
    }
    """
    if not body.outline_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="outline_text must not be blank.",
        )

    parsed = outline_text_to_request_dict(body.outline_text)
    chapters = parsed["chapters"]
    warnings = parsed["warnings"]

    # Hard-error check
    hard_errors = [w for w in warnings if not w.startswith("⚠")]
    if not chapters or hard_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Outline could not be parsed.",
                "errors":  hard_errors,
            },
        )

    return {
        "chapters":       chapters,
        "chapters_count": len(chapters),
        "warnings":       [w for w in warnings if w.startswith("⚠")],
    }


# ── GET /set-chapter-outline ──────────────────────────────────────────────────

@router.get(
    "",
    summary="Retrieve the active chapter outline",
)
def get_chapter_outline():
    """
    Return the currently active chapter outline, or 404 if none has been set.

    Response includes `original_text` (the author's raw input) and
    `metadata` (source_type, created_at) when available.
    """
    outline = get_active_outline()
    if outline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chapter outline has been set. POST to /set-chapter-outline first.",
        )
    return {"active": True, **outline}


# ── DELETE /set-chapter-outline ───────────────────────────────────────────────

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
