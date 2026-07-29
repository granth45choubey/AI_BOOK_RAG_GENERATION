"""
Export Engine API routes.

POST /export/book     — persist structured book JSON
POST /export/docx     — export editable Word manuscript
POST /export/pdf      — export printable PDF (via DOCX conversion)
GET  /export/download/{filename} — download generated file
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse

from app.schemas.export import (
    ExportErrorResponse,
    ExportRequest,
    ExportSuccessResponse,
    SaveBookRequest,
    StructuredBook,
)
from app.services.export_service import (
    ExportError,
    PdfConversionError,
    export_docx,
    export_pdf,
    get_export_file,
    save_generated_book,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["Export Engine"])


def _error_response(
    exc: ExportError,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    body = ExportErrorResponse(error=exc.message, detail=exc.detail)
    return JSONResponse(status_code=status_code, content=body.model_dump())


@router.post(
    "/book",
    summary="Save structured book for export",
    response_model=dict,
)
def save_book(body: SaveBookRequest):
    """Persist structured book JSON produced by the Book Writing Engine."""
    try:
        path = save_generated_book(body.book)
        return {
            "status": "success",
            "message": "Structured book saved for export.",
            "chapters_count": len(body.book.chapters),
            "stored_at": str(path),
        }
    except ExportError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Failed to save structured book")
        raise HTTPException(status_code=500, detail="Failed to save structured book.") from exc


@router.get(
    "/book",
    summary="Get saved structured book",
    response_model=StructuredBook,
)
def get_book():
    """Return the last saved structured book, if any."""
    from app.services.export_service import load_generated_book

    book = load_generated_book()
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generated book found.",
        )
    return book


def _export_response(
    file_path,
    download_url: str,
    *,
    message: Optional[str] = None,
) -> ExportSuccessResponse:
    return ExportSuccessResponse(
        file_name=file_path.name,
        download_url=download_url,
        message=message,
    )


@router.post(
    "/docx",
    summary="Export book as editable DOCX",
    responses={
        200: {"model": ExportSuccessResponse},
        400: {"model": ExportErrorResponse},
    },
)
def export_book_docx(body: ExportRequest = Body(default_factory=ExportRequest)):
    """Convert the structured book into a professionally formatted Word document."""
    from app.services.export_service import resolve_book

    try:
        book = resolve_book(body.book)
        file_path, download_url = export_docx(book)
        return _export_response(
            file_path,
            download_url,
            message="Editable DOCX generated successfully.",
        )
    except ExportError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if "No generated book found" in exc.message
            else status.HTTP_400_BAD_REQUEST
        )
        return _error_response(exc, code)
    except Exception as exc:
        logger.exception("DOCX export failed")
        return _error_response(ExportError("DOCX export failed.", detail=str(exc)), 500)


@router.post(
    "/pdf",
    summary="Export book as PDF",
    responses={
        200: {"model": ExportSuccessResponse},
        400: {"model": ExportErrorResponse},
        503: {"model": ExportErrorResponse},
    },
)
def export_book_pdf(body: ExportRequest = Body(default_factory=ExportRequest)):
    """Convert the structured book to PDF via DOCX → PDF conversion."""
    from app.services.export_service import resolve_book

    try:
        book = resolve_book(body.book)
        file_path, download_url = export_pdf(book)
        return _export_response(
            file_path,
            download_url,
            message="PDF generated successfully.",
        )
    except PdfConversionError as exc:
        return _error_response(exc, status.HTTP_503_SERVICE_UNAVAILABLE)
    except ExportError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if "No generated book found" in exc.message
            else status.HTTP_400_BAD_REQUEST
        )
        return _error_response(exc, code)
    except Exception as exc:
        logger.exception("PDF export failed")
        return _error_response(ExportError("PDF export failed.", detail=str(exc)), 500)


@router.get(
    "/download/{filename}",
    summary="Download exported file",
    response_class=FileResponse,
)
def download_export(filename: str):
    """Download a previously generated export file."""
    try:
        path = get_export_file(filename)
    except ExportError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc

    media_type = (
        "application/pdf"
        if filename.lower().endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path=str(path),
        filename=filename,
        media_type=media_type,
    )
