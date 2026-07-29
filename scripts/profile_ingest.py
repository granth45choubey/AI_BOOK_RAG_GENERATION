"""Profile document ingestion stages for one PDF."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.file_parser import parse_file
from app.rag_pipeline.chunker import chunk_documents
from app.rag_pipeline.embedder import embed_documents
from app.utils.config import get_settings

settings = get_settings()


def profile(pdf_path: str) -> None:
    print(f"\n=== Profiling: {pdf_path} ===")
    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")

    t0 = time.perf_counter()
    pages = parse_file(pdf_path)
    t_parse = time.perf_counter() - t0
    print(f"Parse: {t_parse:.2f}s | pages={len(pages)} | chars={sum(len(p['text']) for p in pages):,}")

    t0 = time.perf_counter()
    chunks = chunk_documents(pages)
    t_chunk = time.perf_counter() - t0
    print(f"Chunk: {t_chunk:.2f}s | chunks={len(chunks)} | chunk_size={settings.chunk_size}")

    # Batch embed (optimized path)
    t0 = time.perf_counter()
    embed_documents([c["text"] for c in chunks])
    t_batch = time.perf_counter() - t0
    print(
        f"Embed (Ollama native batch, all {len(chunks)} chunks): {t_batch:.2f}s "
        f"| ~{t_batch/len(chunks):.3f}s/chunk"
    )


if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else str(
        ROOT / "uploaded_docs" / "12 Articles on Productivity.pdf"
    )
    profile(pdf)
