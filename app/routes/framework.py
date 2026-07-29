"""
Framework Generator Agent — API routes.

POST /generate-frameworks
    → Accepts optional book_context, competitor_analysis, retrieved_docs overrides.
    → Returns 3 generated frameworks (chapter breakdown, transformation flow, unique angle).

POST /select-framework
    → Accepts framework_id.
    → Persists the chosen framework to disk and returns it.

GET /frameworks
    → Returns the currently active (last generated) frameworks.

GET /selected-framework
    → Returns the persisted selected framework (survives restarts).
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services.framework_service import (
    generate_frameworks,
    get_active_frameworks,
    load_selected_framework,
    select_framework,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Framework Generator"])

_fw_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="framework_gen")


# ── Request / Response schemas ─────────────────────────────────────────────────


class BookContextInput(BaseModel):
    """Optional inline book context — overrides the stored context if provided."""
    title: str = Field(..., description="Book title")
    subtitle: Optional[str] = Field(None, description="Subtitle (optional)")
    target_audience: str = Field(..., description="Primary reader group")
    author_objective: Optional[str] = Field(None)
    reader_transformation: Optional[str] = Field(None)
    initial_state: Optional[str] = Field(None, description="Reader state before reading")
    final_state: Optional[str] = Field(None, description="Reader state after reading")
    tone: Optional[str] = Field(None)


class CompetitorAnalysisInput(BaseModel):
    """Optional inline competitor analysis — overrides the cached analysis if provided."""
    patterns: List[str] = Field(default_factory=list)
    common_structures: List[str] = Field(default_factory=list)
    differentiators: List[str] = Field(default_factory=list)


class RetrievedDocInput(BaseModel):
    """A single retrieved document chunk."""
    text: str
    source: str = "unknown"
    page: int = 0


class GenerateFrameworksRequest(BaseModel):
    """
    POST /generate-frameworks body.

    All fields are optional; when omitted the agent pulls data from:
      - book_context     → ChromaDB (book_context_active)
      - competitor_analysis → competitor_docs/analysis_cache.json
      - retrieved_docs   → Live layered RAG retrieval
    """
    book_context: Optional[BookContextInput] = Field(
        None,
        description="Inline book context (overrides stored context)",
    )
    competitor_analysis: Optional[CompetitorAnalysisInput] = Field(
        None,
        description="Inline competitor analysis (overrides cached analysis)",
    )
    retrieved_docs: Optional[List[RetrievedDocInput]] = Field(
        None,
        description="Pre-retrieved docs (overrides live RAG retrieval)",
    )
    force_regenerate: bool = Field(
        False,
        description="Bypass disk cache and call the LLM even if inputs are unchanged",
    )


class SelectFrameworkRequest(BaseModel):
    framework_id: str = Field(
        ...,
        description="The framework_id returned by /generate-frameworks (e.g. 'framework_a')",
        examples=["framework_a"],
    )


# ── Helper: convert Pydantic input to plain dicts ──────────────────────────────

def _ctx_to_dict(ctx: Optional[BookContextInput]) -> Optional[Dict[str, Any]]:
    return ctx.model_dump() if ctx else None


def _competitor_to_dict(
    comp: Optional[CompetitorAnalysisInput],
) -> Optional[Dict[str, Any]]:
    return comp.model_dump() if comp else None


def _docs_to_list(
    docs: Optional[List[RetrievedDocInput]],
) -> Optional[List[Dict[str, Any]]]:
    if docs is None:
        return None
    return [d.model_dump() for d in docs]


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post(
    "/generate-frameworks",
    summary="Generate 3 book frameworks",
    status_code=status.HTTP_200_OK,
)
async def generate_frameworks_endpoint(body: GenerateFrameworksRequest = GenerateFrameworksRequest()):
    """
    **Framework Generator Agent** — Generate 3 distinct book frameworks.

    Each framework includes:
    - `framework_id`            : stable slug used to select this framework
    - `name`                    : short human-readable title
    - `unique_angle`            : differentiating philosophy / hook
    - `flow_of_transformation`  : `{before, journey, after}` reader arc
    - `chapter_breakdown`       : list of chapters with title, purpose & key concepts

    **Data sources** (in priority order):
    1. Inline `book_context` field in request body (if provided)
    2. Stored book context in ChromaDB (`/set-book-context`)
    3. Inline `competitor_analysis` (if provided) or cached analysis
    4. Inline `retrieved_docs` (if provided) or live RAG retrieval
    """
    try:
        loop = asyncio.get_running_loop()
        fn = partial(
            generate_frameworks,
            book_context_override=_ctx_to_dict(body.book_context),
            competitor_analysis_override=_competitor_to_dict(body.competitor_analysis),
            retrieved_docs_override=_docs_to_list(body.retrieved_docs),
            force_regenerate=body.force_regenerate,
        )
        frameworks = await loop.run_in_executor(_fw_executor, fn)
    except Exception as exc:
        logger.error("Framework generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Framework generation failed: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message":     f"Generated {len(frameworks)} frameworks successfully.",
            "count":       len(frameworks),
            "frameworks":  frameworks,
        },
    )


@router.post(
    "/select-framework",
    summary="Select a framework as the active book structure",
    status_code=status.HTTP_200_OK,
)
def select_framework_endpoint(body: SelectFrameworkRequest):
    """
    Mark one of the generated frameworks as the **selected framework**.

    - The selected framework is persisted to disk and survives server restarts.
    - Call `GET /selected-framework` to retrieve it at any time.
    - Call `POST /generate-frameworks` first to populate the available frameworks.
    """
    try:
        selected = select_framework(body.framework_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Framework selection failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Framework selection failed: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message":   f"Framework '{selected['name']}' selected and saved.",
            "framework": selected,
        },
    )


@router.get(
    "/frameworks",
    summary="List the last generated frameworks (in-memory)",
    status_code=status.HTTP_200_OK,
)
def list_frameworks():
    """
    Return the frameworks generated during the **current server session**.

    Returns 404 if no frameworks have been generated since the server started.
    Use `POST /generate-frameworks` to generate them.
    """
    frameworks = get_active_frameworks()
    if not frameworks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No frameworks have been generated yet. POST to /generate-frameworks first.",
        )
    return {"count": len(frameworks), "frameworks": frameworks}


@router.get(
    "/selected-framework",
    summary="Retrieve the persisted selected framework",
    status_code=status.HTTP_200_OK,
)
def get_selected_framework():
    """
    Return the **currently selected** framework (loaded from disk).

    Survives server restarts. Returns 404 if no framework has been selected yet.
    """
    fw = load_selected_framework()
    if not fw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No framework has been selected yet. POST to /select-framework first.",
        )
    return {"selected": True, "framework": fw}
