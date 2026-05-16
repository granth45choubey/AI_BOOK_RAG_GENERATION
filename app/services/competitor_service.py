"""
Competitor Analysis Service — background jobs + orchestration.

Job lifecycle: pending → processing → completed | failed

Cache modes:
  replace — clears competitor collection + cache, starts fresh (default)
  merge   — keeps existing data, appends new books
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.rag_pipeline.chunker import chunk_documents
from app.rag_pipeline.competitor_extractor import analyze_book
from app.rag_pipeline.embedder import get_embedding_function
from app.utils.config import get_settings
from app.utils.file_parser import parse_file

logger = logging.getLogger(__name__)
settings = get_settings()

# ── In-memory job store (swap for Redis in production) ────────────────────────
_JOB_STORE: Dict[str, Dict[str, Any]] = {}

# Single-worker pool so Ollama is never overloaded by concurrent jobs
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="competitor")


# ── ChromaDB helpers ──────────────────────────────────────────────────────────

def _chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _get_competitor_collection():
    return _chroma_client().get_or_create_collection(
        name=settings.competitor_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _clear_and_recreate_collection():
    client = _chroma_client()
    try:
        client.delete_collection(settings.competitor_collection_name)
        logger.info("Competitor collection deleted (replace mode).")
    except Exception:
        pass
    return client.get_or_create_collection(
        name=settings.competitor_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _store_competitor_chunks(collection, chunks: List[Dict[str, Any]]) -> int:
    if not chunks:
        return 0
    ef = get_embedding_function()
    batch_size, total = 50, 0
    n_batches = (len(chunks) + batch_size - 1) // batch_size
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts     = [c["text"] for c in batch]
        ids       = [str(uuid.uuid4()) for _ in batch]
        metadatas = [{
            "source": c["source"], "page": int(c["page"]),
            "chunk_index": int(c["chunk_index"]), "doc_type": "competitor",
        } for c in batch]
        vectors = ef.embed_documents(texts)
        collection.upsert(ids=ids, documents=texts, embeddings=vectors, metadatas=metadatas)
        total += len(batch)
        logger.info("Competitor embed batch %d/%d (%d total)", i // batch_size + 1, n_batches, total)
    return total


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path() -> Path:
    p = Path(settings.competitor_upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p / "analysis_cache.json"


def load_latest_cache() -> Optional[Dict[str, Any]]:
    cp = _cache_path()
    if cp.exists():
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Cannot read competitor cache: %s", exc)
    return None


def _save_cache(data: Dict[str, Any]) -> None:
    try:
        _cache_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.warning("Cannot write competitor cache: %s", exc)


def _delete_cache() -> None:
    _cache_path().unlink(missing_ok=True)
    logger.info("Competitor cache cleared.")


# ── Cross-book aggregation ────────────────────────────────────────────────────

_AGGREGATE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a publishing strategist. Given individual book analysis reports below, "
        "produce a cross-book synthesis as ONLY valid JSON (no markdown fences):\n\n"
        '{"patterns":["..."],"common_structures":["..."],"differentiators":["..."]}\n\n'
        "- patterns: writing styles/techniques shared across MOST books (4-8 items)\n"
        "- common_structures: chapter/section layouts recurring in 2+ books (4-8 items)\n"
        "- differentiators: unique angles of specific books, cite book name (4-8 items)",
    ),
    ("human", "Reports:\n\n{reports}"),
])

_AGGREGATE_BUDGET = 14_000


def _aggregate_analyses(book_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    parts = []
    for ba in book_analyses:
        chapters = "\n".join(f"  • {h}" for h in ba.get("chapter_structure", [])) or "  (none detected)"
        parts.append(
            f"## {ba['source']}\n"
            f"Pages: {ba['page_count']} | Chunks: {ba['chunk_count']}\n\n"
            f"### Chapters\n{chapters}\n\n"
            f"### Summary\n{ba.get('summary','')}\n\n"
            f"### Writing Patterns\n{ba.get('writing_patterns','')}\n\n"
            f"### Frameworks\n{ba.get('frameworks','')}"
        )
    combined = ("\n\n" + "─" * 60 + "\n\n").join(parts)[:_AGGREGATE_BUDGET]
    llm = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url, temperature=0.1)
    chain = _AGGREGATE_PROMPT | llm | StrOutputParser()
    try:
        raw = chain.invoke({"reports": combined}).strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()
        parsed = json.loads(raw)
        for key in ("patterns", "common_structures", "differentiators"):
            parsed.setdefault(key, [])
        return parsed
    except json.JSONDecodeError as exc:
        logger.error("Aggregation returned invalid JSON: %s", exc)
        return {"patterns": ["(Aggregation JSON error — see book_details)"], "common_structures": [], "differentiators": []}
    except Exception as exc:
        logger.error("Aggregation LLM failed: %s", exc)
        return {"patterns": [f"(Aggregation failed: {exc})"], "common_structures": [], "differentiators": []}


# ── Job management ────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _get_job_db() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.job_store_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _init_job_db() -> None:
    with _get_job_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS competitor_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                progress TEXT,
                mode TEXT,
                books_json TEXT,
                result_json TEXT,
                error TEXT,
                created_at TEXT,
                completed_at TEXT,
                updated_at TEXT
            )
            """
        )
        conn.commit()


def _mark_stale_jobs() -> None:
    """
    Mark jobs that were pending/processing before a restart as failed.
    """
    with _get_job_db() as conn:
        conn.execute(
            """
            UPDATE competitor_jobs
            SET status = 'failed',
                error = 'Server restarted; job did not complete.',
                progress = 'Marked failed after restart.',
                completed_at = ?,
                updated_at = ?
            WHERE status IN ('pending', 'processing')
            """,
            (_now(), _now()),
        )
        conn.commit()


def _save_job_to_db(job: Dict[str, Any]) -> None:
    with _get_job_db() as conn:
        conn.execute(
            """
            INSERT INTO competitor_jobs (
                job_id, status, progress, mode, books_json, result_json, error,
                created_at, completed_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status = excluded.status,
                progress = excluded.progress,
                mode = excluded.mode,
                books_json = excluded.books_json,
                result_json = excluded.result_json,
                error = excluded.error,
                completed_at = excluded.completed_at,
                updated_at = excluded.updated_at
            """,
            (
                job.get("job_id"),
                job.get("status"),
                job.get("progress"),
                job.get("mode"),
                json.dumps(job.get("books", [])),
                json.dumps(job.get("result")),
                job.get("error"),
                job.get("created_at"),
                job.get("completed_at"),
                _now(),
            ),
        )
        conn.commit()


def _load_job_from_db(job_id: str) -> Optional[Dict[str, Any]]:
    with _get_job_db() as conn:
        cur = conn.execute(
            """
            SELECT job_id, status, progress, mode, books_json, result_json,
                   error, created_at, completed_at
            FROM competitor_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    books = json.loads(row[4]) if row[4] else []
    result = json.loads(row[5]) if row[5] else None
    return {
        "job_id": row[0],
        "status": row[1],
        "progress": row[2],
        "mode": row[3],
        "books": books,
        "result": result,
        "error": row[6],
        "created_at": row[7],
        "completed_at": row[8],
    }


_init_job_db()
_mark_stale_jobs()


def _update_job(job_id: str, **kwargs: Any) -> None:
    if job_id in _JOB_STORE:
        _JOB_STORE[job_id].update(kwargs)
        _save_job_to_db(_JOB_STORE[job_id])


def create_job(file_data: List[Dict[str, Any]], mode: str) -> str:
    job_id = str(uuid.uuid4())
    job = {
        "job_id":       job_id,
        "status":       "pending",
        "progress":     "Queued — waiting for analysis worker…",
        "mode":         mode,
        "books":        [f["filename"] for f in file_data],
        "result":       None,
        "error":        None,
        "created_at":   _now(),
        "completed_at": None,
    }
    _JOB_STORE[job_id] = job
    _save_job_to_db(job)
    logger.info("Job %s created (mode=%s, %d books).", job_id, mode, len(file_data))
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return _JOB_STORE.get(job_id) or _load_job_from_db(job_id)


def submit_analysis_job(job_id: str, file_data: List[Dict[str, Any]], mode: str) -> None:
    _executor.submit(_run_analysis, job_id, file_data, mode)
    logger.info("Job %s submitted to executor.", job_id)


# ── Background worker ─────────────────────────────────────────────────────────

def _failed_entry(source: str, reason: str) -> Dict[str, Any]:
    return {"source": source, "page_count": 0, "chunk_count": 0,
            "chapter_structure": [], "summary": f"(Failed: {reason})",
            "writing_patterns": "", "frameworks": ""}


def _run_analysis(job_id: str, file_data: List[Dict[str, Any]], mode: str) -> None:
    try:
        _update_job(job_id, status="processing", progress="Initialising…")
        os.makedirs(settings.competitor_upload_dir, exist_ok=True)

        # Collection setup
        if mode == "replace":
            _update_job(job_id, progress="Clearing previous competitor data (replace mode)…")
            collection = _clear_and_recreate_collection()
            _delete_cache()
        else:
            _update_job(job_id, progress="Opening existing competitor collection (merge mode)…")
            collection = _get_competitor_collection()

        book_analyses: List[Dict[str, Any]] = []
        total_chunks = 0
        n = len(file_data)

        for idx, item in enumerate(file_data, start=1):
            fname   = item["filename"]
            content = item["content"]
            _update_job(job_id, progress=f"[{idx}/{n}] Saving & parsing '{fname}'…")

            # Save
            save_path = os.path.join(settings.competitor_upload_dir, fname)
            try:
                with open(save_path, "wb") as fh:
                    fh.write(content)
            except Exception as exc:
                book_analyses.append(_failed_entry(fname, f"Save error: {exc}"))
                continue

            # Parse
            try:
                pages = parse_file(save_path)
            except Exception as exc:
                book_analyses.append(_failed_entry(fname, f"Parse error: {exc}"))
                continue

            # Chunk
            chunks = chunk_documents(pages)
            logger.info("'%s': %d pages, %d chunks", fname, len(pages), len(chunks))

            # Embed + store
            _update_job(job_id, progress=f"[{idx}/{n}] Embedding {len(chunks)} chunks for '{fname}'…")
            try:
                total_chunks += _store_competitor_chunks(collection, chunks)
            except Exception as exc:
                book_analyses.append(_failed_entry(fname, f"Embedding error: {exc}"))
                continue

            # Per-book LLM (3 calls)
            _update_job(job_id, progress=f"[{idx}/{n}] LLM analysis of '{fname}' (3 calls)…")
            try:
                ba = analyze_book(pages, chunks, fname)
            except Exception as exc:
                ba = _failed_entry(fname, f"LLM error: {exc}")
                ba.update({"page_count": len(pages), "chunk_count": len(chunks)})
            book_analyses.append(ba)

        # Cross-book aggregation
        _update_job(job_id, progress=f"Cross-book aggregation across {len(book_analyses)} books…")
        aggregated = _aggregate_analyses(book_analyses)

        result: Dict[str, Any] = {
            "patterns":          aggregated.get("patterns", []),
            "common_structures": aggregated.get("common_structures", []),
            "differentiators":   aggregated.get("differentiators", []),
            "books_analyzed":    [ba["source"] for ba in book_analyses],
            "chunks_stored":     total_chunks,
            "mode":              mode,
            "book_details":      book_analyses,
            "timestamp":         _now(),
        }
        _save_cache(result)
        _update_job(job_id, status="completed", progress="Analysis complete ✓",
                    result=result, completed_at=_now())
        logger.info("Job %s completed.", job_id)

    except Exception as exc:
        logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
        _update_job(job_id, status="failed", progress="Analysis failed — see error field.",
                    error=str(exc), completed_at=_now())
