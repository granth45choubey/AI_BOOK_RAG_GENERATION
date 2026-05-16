"""
Template and framework selection routes.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.services.template_service import (
    TemplateSelection,
    TemplateValidationError,
    clear_selected_template,
    get_selected_template,
    list_templates,
    save_selected_template,
)

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", summary="List available templates")
def get_templates():
    return {"templates": [t.model_dump() for t in list_templates()]}


@router.post("/select", summary="Select a template", status_code=status.HTTP_201_CREATED)
def select_template(selection: TemplateSelection):
    available = {t.id for t in list_templates()}
    if selection.template_id not in available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown template_id: {selection.template_id}",
        )
    try:
        result = save_selected_template(selection)
    except TemplateValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=result)


@router.get("/selected", summary="Get selected template")
def get_template_selection():
    current = get_selected_template()
    if not current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No template selected.",
        )
    return current


@router.delete("/selected", summary="Clear selected template")
def clear_template_selection():
    cleared = clear_selected_template()
    if not cleared:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No template selected.",
        )
    return {"message": "Template selection cleared.", "active": False}
