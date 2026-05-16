"""
POST /originality-check

Checks similarity of a draft against stored corpora.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.originality_service import check_originality

router = APIRouter(prefix="/originality-check", tags=["Originality"])


class OriginalityRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Draft text to analyze")
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    include_competitor: bool = True
    include_general: bool = True


@router.post("", status_code=status.HTTP_200_OK)
def originality_check(body: OriginalityRequest):
    try:
        return check_originality(
            text=body.text,
            top_k=body.top_k,
            threshold=body.threshold,
            include_competitor=body.include_competitor,
            include_general=body.include_general,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Originality check failed: {exc}",
        ) from exc
