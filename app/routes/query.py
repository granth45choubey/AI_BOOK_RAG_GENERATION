"""
POST /query

Accepts a question, retrieves relevant chunks from ChromaDB,
and returns an LLM-generated answer with source citations.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.query_service import answer_query

router = APIRouter(prefix="/query", tags=["Query"])

_query_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="query_gen")


# ── Request / Response schemas ────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The question to answer")
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of context chunks to retrieve (default from config)",
    )
    source_filter: Optional[str] = Field(
        default=None,
        description="Restrict retrieval to a specific source filename",
    )


class ChunkResult(BaseModel):
    text: str
    source: str
    page: int
    chunk_index: int
    score: float
    source_type: Optional[str] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    retrieved_chunks: List[ChunkResult]


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post(
    "",
    summary="Query the RAG knowledge base",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
)
async def query_documents(body: QueryRequest):
    """
    Ask a question against the ingested documents.

    Returns an LLM-generated answer grounded in retrieved context,
    along with source citations and the raw retrieved chunks.
    """
    try:
        loop = asyncio.get_running_loop()
        fn = partial(
            answer_query,
            question=body.question,
            top_k=body.top_k,
            source_filter=body.source_filter,
        )
        result = await loop.run_in_executor(_query_executor, fn)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc

    return result
