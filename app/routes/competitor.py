"""
Market & Research Analysis Routes.

New endpoints (Market & Research Analysis):
  POST /analyze-market                    — submit documents for analysis
  GET  /analyze-market/status/{job_id}   — poll job progress
  GET  /analyze-market/latest            — get cached result

Legacy endpoints (Competitor Analysis — backward-compatible):
  POST /analyze-competitors               — same as above with document_type=book
  GET  /analyze-competitors/status/{job_id}
  GET  /analyze-competitors/latest

Both sets of endpoints are registered from this module.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from app.services.market_analysis_service import (
    create_job,
    get_job,
    load_latest_cache,
    submit_analysis_job,
)
from app.rag_pipeline.market_extractor import VALID_DOCUMENT_TYPES
from app.utils.config import get_settings

settings = get_settings()
_SOFT_LIMIT = 5

# ── Routers ────────────────────────────────────────────────────────────────────

# Primary: new market analysis route
market_router = APIRouter(
    prefix="/analyze-market",
    tags=["Market & Research Analysis"],
)

# Legacy: keep old prefix alive (backward-compatible)
competitor_router = APIRouter(
    prefix="/analyze-competitors",
    tags=["Competitor Analysis (Legacy)"],
)


# ══════════════════════════════════════════════════════════════════════════════
# Shared handler — used by both routers
# ══════════════════════════════════════════════════════════════════════════════

async def _handle_submit(
    files: List[UploadFile],
    mode: str,
    document_type: str,
    prefix: str,
) -> JSONResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    if mode not in ("replace", "merge"):
        raise HTTPException(status_code=400, detail="mode must be 'replace' or 'merge'.")

    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"document_type '{document_type}' is not valid. "
                f"Choose one of: {VALID_DOCUMENT_TYPES}"
            ),
        )

    n = len(files)
    hard_limit = settings.max_competitor_books
    if n > hard_limit:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {hard_limit} files allowed per run. You uploaded {n}.",
        )

    warning: str | None = None
    if n > _SOFT_LIMIT:
        warning = (
            f"You uploaded {n} files (above the recommended {_SOFT_LIMIT}). "
            f"Estimated time: {n * 2}–{n * 3} minutes. "
            f"Poll {prefix}/status/{{job_id}} for progress."
        )

    file_data = []
    for f in files:
        content = await f.read()
        file_data.append({"filename": f.filename, "content": content})

    job_id = create_job(file_data, mode, document_type)
    submit_analysis_job(job_id, file_data, mode, document_type)

    est_min = max(3, n * 2)
    body = {
        "job_id":                     job_id,
        "status":                     "pending",
        "mode":                       mode,
        "document_type":              document_type,
        "documents_queued":           [f["filename"] for f in file_data],
        # backward-compat alias
        "books_queued":               [f["filename"] for f in file_data],
        "estimated_duration_minutes": est_min,
        "message": (
            f"Analysis started in background. "
            f"Poll GET {prefix}/status/{job_id} for progress and results."
        ),
    }
    if warning:
        body["warning"] = warning

    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=body)


def _handle_status(job_id: str) -> JSONResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. It may have expired or the server restarted.",
        )
    return JSONResponse(content=job)


def _handle_latest() -> JSONResponse:
    cached = load_latest_cache()
    if not cached:
        raise HTTPException(
            status_code=404,
            detail="No completed analysis found. Submit one first.",
        )
    return JSONResponse(content=cached)


# ══════════════════════════════════════════════════════════════════════════════
# PRIMARY: /analyze-market
# ══════════════════════════════════════════════════════════════════════════════

@market_router.post(
    "",
    summary="Submit documents for Market & Research analysis",
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_market(
    files: List[UploadFile] = File(..., description="PDF documents to analyze"),
    mode: str = Query("replace", description="'replace' or 'merge'"),
    document_type: str = Query(
        "book",
        description=(
            "Type of document: "
            "'book' | 'research_paper' | 'industry_report' | 'whitepaper'"
        ),
    ),
):
    """
    Upload documents for asynchronous market & research analysis.

    **Supported document types:**
    - `book`            — competitor books (chapters, frameworks, writing style)
    - `research_paper`  — academic papers (findings, statistics, evidence, trends)
    - `industry_report` — market reports (trends, opportunities, challenges, outlook)
    - `whitepaper`      — technical papers (models, methodologies, recommendations)

    Returns **202 Accepted** with `job_id`. Poll `/analyze-market/status/{job_id}`.
    """
    return await _handle_submit(files, mode, document_type, "/analyze-market")


@market_router.get(
    "/status/{job_id}",
    summary="Poll market analysis job status",
)
def get_market_status(job_id: str):
    """Poll the status of a market analysis job."""
    return _handle_status(job_id)


@market_router.get(
    "/latest",
    summary="Get the latest cached market analysis result",
)
def get_market_latest():
    """Return the most recently completed analysis from the JSON cache."""
    return _handle_latest()


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY: /analyze-competitors  (backward-compatible, document_type fixed=book)
# ══════════════════════════════════════════════════════════════════════════════

@competitor_router.post(
    "",
    summary="[Legacy] Submit competitor PDFs for background analysis",
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_competitors_legacy(
    files: List[UploadFile] = File(..., description="PDF files of competitor books"),
    mode: str = Query("replace", description="'replace' or 'merge'"),
):
    """
    Legacy endpoint — identical to `POST /analyze-market` with `document_type=book`.

    Kept for backward compatibility. Prefer `/analyze-market` for new integrations.
    """
    return await _handle_submit(files, mode, "book", "/analyze-competitors")


@competitor_router.get(
    "/status/{job_id}",
    summary="[Legacy] Poll competitor analysis job status",
)
def get_competitor_status_legacy(job_id: str):
    return _handle_status(job_id)


@competitor_router.get(
    "/latest",
    summary="[Legacy] Get the latest cached competitor analysis result",
)
def get_competitor_latest_legacy():
    return _handle_latest()
