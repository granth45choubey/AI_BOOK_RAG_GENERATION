"""
POST /upload-author-documents

Upload author-specific content (questionnaires, transcripts, notes).
Chunks are stored in the main ChromaDB collection with:
  source_type = "author"
  priority_score = 1.0  (highest)

These chunks are retrieved before all other sources in every query.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.services.author_service import ingest_author_documents_sync

router = APIRouter(prefix="/upload-author-documents", tags=["Author Documents"])

_author_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="author_ingest")


@router.post(
    "",
    summary="Upload author-specific documents (highest retrieval priority)",
    response_description="Ingestion summary with per-file status",
    status_code=status.HTTP_201_CREATED,
)
async def upload_author_documents(
    files: List[UploadFile] = File(
        ...,
        description="PDF, DOCX, or TXT files containing author-specific content "
                    "(questionnaires, transcripts, notes, etc.)",
    ),
):
    """
    Upload one or more author-specific documents into the RAG knowledge base.

    Stored chunks receive **source_type=author** and **priority_score=1.0**,
    so they are always retrieved first and have the strongest influence on
    LLM-generated content.

    - Supports: PDF, DOCX, TXT
    - Uses the same chunking/embedding pipeline as `/upload-documents`
    - Embedding is offloaded to a thread-pool to keep the event loop free
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided.",
        )

    file_data: List[dict] = []
    for f in files:
        content = await f.read()
        file_data.append({"filename": f.filename, "content": content})

    try:
        loop = asyncio.get_running_loop()
        summary = await loop.run_in_executor(
            _author_executor,
            ingest_author_documents_sync,
            file_data,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Author document ingestion failed: {exc}",
        ) from exc

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=summary)
