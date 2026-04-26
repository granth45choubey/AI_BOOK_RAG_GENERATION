"""
POST /upload-documents

Accepts one or more PDF/DOCX/TXT files, parses + chunks + embeds them,
and stores the result in ChromaDB.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.services.document_service import ingest_documents_sync

router = APIRouter(prefix="/upload-documents", tags=["Documents"])

# Dedicated thread-pool for CPU/network-bound ingestion work
_ingest_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingest")


@router.post(
    "",
    summary="Upload and ingest documents",
    response_description="Ingestion summary with per-file status",
    status_code=status.HTTP_201_CREATED,
)
async def upload_documents(
    files: List[UploadFile] = File(default=[], description="PDF, DOCX, or TXT files"),
):
    """
    Upload one or more documents for ingestion into the RAG knowledge base.

    - Files are parsed to extract text (with page metadata).
    - Text is chunked using the configured strategy.
    - Chunks are embedded and stored in ChromaDB.

    Note: embedding via Ollama is CPU/network-bound so we offload it to a
    thread-pool executor so the async event loop is never blocked.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided.",
        )

    # Read all file bytes eagerly while still in the async context, then
    # hand plain data (filename + bytes) to the sync worker thread.
    file_data: List[dict] = []
    for f in files:
        content = await f.read()
        file_data.append({"filename": f.filename, "content": content})

    try:
        loop = asyncio.get_running_loop()
        summary = await loop.run_in_executor(
            _ingest_executor,
            ingest_documents_sync,
            file_data,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {exc}",
        ) from exc

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=summary)
