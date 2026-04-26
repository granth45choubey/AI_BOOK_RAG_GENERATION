"""
Competitor Analysis Routes.

POST /analyze-competitors
    Upload 5–10 competitor PDFs. Returns 202 with job_id immediately.
    Background worker runs the full analysis pipeline.

GET  /analyze-competitors/status/{job_id}
    Poll for live progress and final result.

GET  /analyze-competitors/latest
    Return the latest cached completed result (if any).
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from app.services.competitor_service import (
    create_job,
    get_job,
    load_latest_cache,
    submit_analysis_job,
)
from app.utils.config import get_settings

router = APIRouter(prefix="/analyze-competitors", tags=["Competitor Analysis"])
settings = get_settings()

# Soft default: warn beyond this; hard limit from config (max_competitor_books)
_SOFT_LIMIT = 5


@router.post(
    "",
    summary="Submit competitor PDFs for background analysis",
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Job ID and status — poll /status/{job_id} for results",
)
async def analyze_competitors(
    files: List[UploadFile] = File(..., description="PDF files of competitor books"),
    mode: str = Query(
        "replace",
        description=(
            "'replace' (default) — clear previous analysis and reprocess. "
            "'merge' — combine with existing analysis."
        ),
    ),
):
    """
    Upload 5–10 competitor PDF books for asynchronous analysis.

    - Returns **202 Accepted** with a `job_id` immediately.
    - The full pipeline (parse → embed → per-book LLM → aggregation) runs in the background.
    - Poll `GET /analyze-competitors/status/{job_id}` for live progress.
    - Default `mode=replace` clears all previous competitor data before processing.
    """
    # ── Validate inputs ───────────────────────────────────────────────────────
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided.")

    if mode not in ("replace", "merge"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mode must be 'replace' or 'merge'.",
        )

    n = len(files)
    hard_limit = settings.max_competitor_books
    if n > hard_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Maximum {hard_limit} books allowed per analysis run. "
                f"You uploaded {n}. Please reduce the number of files."
            ),
        )

    warning: str | None = None
    if n > _SOFT_LIMIT:
        warning = (
            f"You uploaded {n} books (above the recommended {_SOFT_LIMIT}). "
            f"Estimated analysis time: {n * 2}–{n * 3} minutes. "
            "The job runs in the background — poll /status/{job_id} for updates."
        )

    # ── Read file bytes (must stay in async context) ──────────────────────────
    file_data: List[dict] = []
    for f in files:
        content = await f.read()
        file_data.append({"filename": f.filename, "content": content})

    # ── Create + submit job ───────────────────────────────────────────────────
    job_id = create_job(file_data, mode)
    submit_analysis_job(job_id, file_data, mode)

    est_min = max(3, n * 2)
    response_body = {
        "job_id":                   job_id,
        "status":                   "pending",
        "mode":                     mode,
        "books_queued":             [f["filename"] for f in file_data],
        "estimated_duration_minutes": est_min,
        "message": (
            f"Analysis started in background. "
            f"Poll GET /analyze-competitors/status/{job_id} for progress and results."
        ),
    }
    if warning:
        response_body["warning"] = warning

    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response_body)


@router.get(
    "/status/{job_id}",
    summary="Poll competitor analysis job status",
    response_description="Job status, progress message, and result when complete",
)
def get_analysis_status(job_id: str):
    """
    Poll the status of a competitor analysis job.

    Returns one of:
    - `status: "pending"`   — job is queued
    - `status: "processing"` — analysis is running; see `progress` for current step
    - `status: "completed"` — `result` field contains the full analysis
    - `status: "failed"`    — `error` field contains the failure reason
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found. It may have expired or the server restarted.",
        )
    return JSONResponse(content=job)


@router.get(
    "/latest",
    summary="Get the latest cached competitor analysis result",
    response_description="Most recently completed analysis result",
)
def get_latest_analysis():
    """
    Return the most recently completed competitor analysis from the JSON cache.

    Useful to retrieve results after a server restart (job store is in-memory,
    but the cache file is persisted to disk).
    """
    cached = load_latest_cache()
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No completed competitor analysis found. "
                "Submit one via POST /analyze-competitors first."
            ),
        )
    return JSONResponse(content=cached)
