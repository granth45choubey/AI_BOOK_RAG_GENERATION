"""
Orchestration endpoints used by the guided Author Studio UI.

These routes compose existing services to deliver one-click flows:

  POST /orchestrate/auto-blueprint
      Select a template (defaulting to ``classic_nonfiction``), prefill an
      outline from it, save the outline, and return the saved outline.

  POST /orchestrate/draft-chapter
      Construct a chapter-scoped drafting prompt from the active outline
      and run it through the standard RAG query pipeline. Returns the
      generated draft, retrieved sources, and originality report.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.outline_service import (
    Chapter,
    ChapterOutlineRequest,
    ChapterSection,
    get_active_outline,
    prefill_outline_from_template,
    save_outline,
)
from app.services.query_service import answer_query
from app.services.template_service import (
    TemplateSelection,
    TemplateValidationError,
    list_templates,
    save_selected_template,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orchestrate", tags=["Orchestration"])


# ── Auto-blueprint ────────────────────────────────────────────────────────────

class AutoBlueprintRequest(BaseModel):
    template_id: Optional[str] = Field(
        default=None,
        description="Template id to use. Defaults to 'classic_nonfiction' if omitted.",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional template parameters (audience, tone, pages).",
    )


@router.post(
    "/auto-blueprint",
    summary="Select a template, prefill an outline, and save it in one call",
    status_code=status.HTTP_201_CREATED,
)
def auto_blueprint(body: AutoBlueprintRequest):
    available = {t.id: t for t in list_templates()}
    template_id = body.template_id or "classic_nonfiction"
    if template_id not in available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown template_id: {template_id}",
        )

    try:
        selected = save_selected_template(
            TemplateSelection(template_id=template_id, parameters=body.parameters or {})
        )
    except TemplateValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    prefilled = prefill_outline_from_template()
    if prefilled is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not prefill outline from the selected template.",
        )

    try:
        saved = save_outline(ChapterOutlineRequest(chapters=prefilled.chapters))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save generated outline: {exc}",
        ) from exc

    return {
        "template": selected,
        "chapters": saved["chapters"],
        "chapters_count": saved["chapters_count"],
        "outline_text": saved["outline_text"],
    }


# ── Draft chapter ─────────────────────────────────────────────────────────────

class DraftChapterRequest(BaseModel):
    chapter_index: int = Field(..., ge=0, description="Zero-based chapter index.")
    instructions: Optional[str] = Field(
        default=None,
        description="Optional additional drafting guidance (tone, focus, redraft notes).",
    )
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    source_filter: Optional[str] = Field(default=None)


@router.post(
    "/draft-chapter",
    summary="Draft a single chapter from the active outline using the RAG pipeline",
)
def draft_chapter(body: DraftChapterRequest):
    outline = get_active_outline()
    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active outline. Build a blueprint first.",
        )

    chapters: List[Dict[str, Any]] = outline.get("chapters", []) or []
    if body.chapter_index >= len(chapters):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"chapter_index {body.chapter_index} out of range (have {len(chapters)} chapters).",
        )

    chapter = chapters[body.chapter_index]
    title = chapter.get("title") or f"Chapter {body.chapter_index + 1}"
    sections = chapter.get("sections", []) or []
    section_lines = [
        f"- {s.get('title', 'Untitled')}" + (f": {s['description']}" if s.get("description") else "")
        for s in sections
    ]
    section_block = "\n".join(section_lines) if section_lines else "(no sections specified)"

    extra = (body.instructions or "").strip()
    extra_block = f"\n\nAdditional author instructions:\n{extra}" if extra else ""

    question = (
        f"Draft Chapter {body.chapter_index + 1}: {title}.\n"
        f"Cover these sections in order, weaving them into a cohesive narrative:\n"
        f"{section_block}\n\n"
        f"Write the chapter as the author would, grounded in the supplied sources. "
        f"Maintain the book's voice and audience throughout."
        f"{extra_block}"
    )

    try:
        result = answer_query(
            question=question,
            top_k=body.top_k,
            source_filter=body.source_filter,
        )
    except Exception as exc:
        logger.exception("Chapter drafting failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chapter drafting failed: {exc}",
        ) from exc

    return {
        "chapter_index": body.chapter_index,
        "chapter_title": title,
        **result,
    }
