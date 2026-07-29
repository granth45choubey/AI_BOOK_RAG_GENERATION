"""
Pydantic schemas for the Export Engine.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BookSection(BaseModel):
    """A section within a chapter."""

    heading: str = Field(..., min_length=1, description="Section heading")
    content: str = Field(default="", description="Section body text")


class BookChapter(BaseModel):
    """A single book chapter."""

    title: str = Field(..., min_length=1, description="Chapter title")
    content: str = Field(
        default="",
        description="Optional chapter introduction before sections",
    )
    sections: List[BookSection] = Field(
        default_factory=list,
        description="Ordered sections within the chapter",
    )


class StructuredBook(BaseModel):
    """Structured book produced by the Book Writing Engine."""

    title: str = Field(..., min_length=1, description="Book title")
    subtitle: Optional[str] = Field(None, description="Book subtitle")
    author: Optional[str] = Field(None, description="Author name")
    chapters: List[BookChapter] = Field(
        ...,
        min_length=1,
        description="Ordered chapter list",
    )


class SaveBookRequest(BaseModel):
    """Persist structured book JSON for export."""

    book: StructuredBook


class ExportRequest(BaseModel):
    """Optional inline book override for export endpoints."""

    book: Optional[StructuredBook] = Field(
        None,
        description="When omitted, the last saved structured book is used",
    )


class ExportSuccessResponse(BaseModel):
    """Successful export response with download URL."""

    status: str = "success"
    file_name: str
    download_url: str
    message: Optional[str] = None


class ExportErrorResponse(BaseModel):
    """Export failure response."""

    status: str = "error"
    error: str
    detail: Optional[str] = None
