"""
Central configuration for the RAG system.
All embedding, LLM, chunking, and storage settings are controlled here.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Ollama / LLM ─────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # ── Embedding ─────────────────────────────────────────────────────────────
    # "ollama" uses the same Ollama server for embeddings
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"   # fast & accurate for RAG

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "rag_documents"

    # ── Chunking ─────────────────────────────────────────────────────────────
    # "recursive" or "semantic"
    chunk_strategy: str = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 64

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieval_top_k: int = 5

    # ── Upload ────────────────────────────────────────────────────────────────
    upload_dir: str = "./uploaded_docs"
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
