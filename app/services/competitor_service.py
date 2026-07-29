"""
Competitor Analysis Service — backward-compatible shim.

All logic has been moved to market_analysis_service.py.
This module re-exports the public API expected by the existing
/analyze-competitors route so no route changes are required for backward compat.
"""
from app.services.market_analysis_service import (
    create_job,
    get_job,
    load_latest_cache,
    submit_analysis_job as _submit,
)
from typing import Any, Dict, List


def submit_analysis_job(job_id: str, file_data: List[Dict[str, Any]], mode: str) -> None:
    """Legacy wrapper — treats all files as competitor 'book' documents."""
    _submit(job_id, file_data, mode, document_type="book")


__all__ = ["create_job", "get_job", "load_latest_cache", "submit_analysis_job"]
