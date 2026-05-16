"""
POST /drafts/export

Exports a full draft from chapter content.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.draft_service import export_draft, save_draft, list_drafts, get_draft, delete_draft

router = APIRouter(prefix="/drafts", tags=["Drafts"])


class DraftChapter(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class DraftExportRequest(BaseModel):
    title: str = Field(..., min_length=1)
    chapters: List[DraftChapter]


@router.post("/export", status_code=status.HTTP_200_OK)
def export_full_draft(body: DraftExportRequest):
    try:
        draft = export_draft(
            title=body.title,
            chapters=[c.model_dump() for c in body.chapters],
        )
        return save_draft(draft)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Draft export failed: {exc}",
        ) from exc


@router.get("", status_code=status.HTTP_200_OK)
def list_all_drafts():
    return {"drafts": list_drafts()}


@router.get("/{draft_id}", status_code=status.HTTP_200_OK)
def get_draft_by_id(draft_id: str):
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found.",
        )
    return draft


@router.delete("/{draft_id}", status_code=status.HTTP_200_OK)
def delete_draft_by_id(draft_id: str):
    deleted = delete_draft(draft_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found.",
        )
    return {"message": "Draft deleted.", "id": draft_id}
