"""
FastAPI application entry point.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import upload, query, book_context
from app.utils.config import get_settings

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    logger.info("RAG system starting up.")
    logger.info("Upload dir     : %s", settings.upload_dir)
    logger.info("ChromaDB dir   : %s", settings.chroma_persist_dir)
    logger.info("Embedding model: %s (%s)", settings.embedding_model, settings.embedding_provider)
    logger.info("LLM model      : %s", settings.ollama_model)
    logger.info("Chunk strategy : %s (size=%d, overlap=%d)", settings.chunk_strategy, settings.chunk_size, settings.chunk_overlap)
    yield
    logger.info("RAG system shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Modular RAG API",
    description=(
        "A production-ready Retrieval-Augmented Generation backend powered by "
        "FastAPI, LangChain, ChromaDB, and Ollama (llama3.1:8b)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(query.router)
app.include_router(book_context.router)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "llm_model": settings.ollama_model,
        "embedding_model": settings.embedding_model,
        "chunk_strategy": settings.chunk_strategy,
    }
