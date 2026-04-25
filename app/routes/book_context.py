"""
POST /create-book-context

Accepts structured book metadata, stores it as a high-priority ChromaDB
document, and returns the formatted context that will be injected into every
subsequent RAG query prompt.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.book_context_service import (
    create_book_context,
    get_active_book_context_struct,
)

router = APIRouter(prefix="/create-book-context", tags=["Book Context"])


# ── Request / Response schemas ────────────────────────────────────────────────

class BookContextRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Book title")
    subtitle: Optional[str] = Field(default="", description="Optional subtitle")
    target_audience: str = Field(..., min_length=1, description="Who the book is written for")
    author_objective: str = Field(..., min_length=1, description="What the author aims to achieve")
    reader_transformation: str = Field(
        ..., min_length=1,
        description="How the reader will be transformed by reading this book"
    )
    initial_state: str = Field(
        ..., min_length=1,
        description="The reader's knowledge / mindset BEFORE reading"
    )
    final_state: str = Field(
        ..., min_length=1,
        description="The reader's knowledge / mindset AFTER reading"
    )
    tone: str = Field(..., min_length=1, description="Writing tone and style (e.g. 'authoritative yet approachable')")


class BookContextResponse(BaseModel):
    message: str
    context_text: str
    title: str
    subtitle: str
    target_audience: str
    author_objective: str
    reader_transformation: str
    initial_state: str
    final_state: str
    tone: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    summary="Create or update the book context",
    response_model=BookContextResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_context(body: BookContextRequest):
    """
    Store structured book metadata as a high-priority vector document.

    This context is automatically injected into **every** subsequent RAG
    query so the LLM always writes with the book's goals and audience in mind.

    Calling this endpoint again will **replace** the existing context.
    """
    try:
        result = create_book_context(
            title=body.title,
            subtitle=body.subtitle or "",
            target_audience=body.target_audience,
            author_objective=body.author_objective,
            reader_transformation=body.reader_transformation,
            initial_state=body.initial_state,
            final_state=body.final_state,
            tone=body.tone,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store book context: {exc}",
        ) from exc

    return BookContextResponse(
        message="Book context created successfully. It will be injected into every RAG query.",
        **result,
    )


@router.get(
    "",
    summary="Retrieve the active book context",
    status_code=status.HTTP_200_OK,
)
def get_context():
    """
    Return the currently active book context, or a message if none is set.
    """
    struct = get_active_book_context_struct()
    if struct is None:
        return {"active": False, "message": "No book context has been set yet."}
    return {"active": True, **struct}
