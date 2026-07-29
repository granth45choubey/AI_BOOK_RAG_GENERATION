"""
Market & Research Analysis Service — background jobs + orchestration.

Extends (and supersedes) the original competitor_service for all document types.

Supported document_type values:
  book            — competitor books (backward-compatible)
  research_paper  — academic / empirical research papers
  industry_report — market sizing, trend, and opportunity reports
  whitepaper      — technical / strategic whitepapers

Job lifecycle:  pending → processing → completed | failed

Cache modes:
  replace — clears market analysis collection + cache, starts fresh (default)
  merge   — keeps existing data, appends new documents

Metadata stored per chunk:
  source_type     : "market_analysis"
  document_type   : "book" | "research_paper" | "industry_report" | "whitepaper"
  priority_score  : float (varies by type)
  doc_type        : "competitor"  (legacy compat key)

Priority scores by document type:
  research_paper  → 0.85  (highest — empirical grounding)
  industry_report → 0.80
  whitepaper      → 0.75
  book            → 0.70  (was "competitor", same collection)
"""
from __future__ import annotations

import json
import logging
import os
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
from app.rag_pipeline.market_extractor import analyze_document, VALID_DOCUMENT_TYPES
from app.rag_pipeline.embedder import embed_documents
from app.utils.config import get_settings
from app.utils.file_parser import parse_file

logger = logging.getLogger(__name__)
settings = get_settings()

# ── In-memory job store ───────────────────────────────────────────────────────
_JOB_STORE: Dict[str, Dict[str, Any]] = {}

# Single-worker pool — Ollama is never overloaded by concurrent jobs
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="market_analysis")

# Priority scores per document type
_PRIORITY_SCORES: Dict[str, float] = {
    "research_paper":  0.85,
    "industry_report": 0.80,
    "whitepaper":      0.75,
    "book":            0.70,
}


# ── ChromaDB helpers ──────────────────────────────────────────────────────────

def _chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _get_market_collection():
    """Returns the shared competitor/market collection."""
    return _chroma_client().get_or_create_collection(
        name=settings.competitor_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _clear_and_recreate_collection():
    client = _chroma_client()
    try:
        client.delete_collection(settings.competitor_collection_name)
        logger.info("Market analysis collection deleted (replace mode).")
    except Exception:
        pass
    return client.get_or_create_collection(
        name=settings.competitor_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _store_market_chunks(
    collection,
    chunks: List[Dict[str, Any]],
    document_type: str,
) -> int:
    """Embed and store chunks with enriched market_analysis metadata."""
    if not chunks:
        return 0

    priority_score = _PRIORITY_SCORES.get(document_type, 0.70)
    batch_size = max(1, settings.embedding_batch_size)
    total = 0
    n_batches = (len(chunks) + batch_size - 1) // batch_size

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        texts     = [c["text"] for c in batch]
        ids       = [str(uuid.uuid4()) for _ in batch]
        metadatas = [
            {
                "source":         c["source"],
                "page":           int(c["page"]),
                "chunk_index":    int(c["chunk_index"]),
                # New enriched metadata
                "source_type":    "market_analysis",
                "document_type":  document_type,
                "priority_score": priority_score,
                # Backward-compat key kept for existing queries
                "doc_type":       "competitor",
            }
            for c in batch
        ]
        vectors = embed_documents(texts)
        collection.upsert(ids=ids, documents=texts, embeddings=vectors, metadatas=metadatas)
        total += len(batch)
        logger.debug(
            "Market embed batch %d/%d (%d total, type=%s)",
            i // batch_size + 1, n_batches, total, document_type,
        )
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
            logger.warning("Cannot read market analysis cache: %s", exc)
    return None


def _save_cache(data: Dict[str, Any]) -> None:
    try:
        _cache_path().write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("Cannot write market analysis cache: %s", exc)


def _delete_cache() -> None:
    _cache_path().unlink(missing_ok=True)
    logger.info("Market analysis cache cleared.")


# ── Cross-document aggregation ────────────────────────────────────────────────

_AGGREGATE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a market intelligence strategist. "
        "Given individual document analysis reports below (may include books, research papers, "
        "industry reports, whitepapers), produce a cross-document synthesis as ONLY valid JSON "
        "(no markdown fences):\n\n"
        '{"patterns":["..."],"common_structures":["..."],"differentiators":["..."],'
        '"key_trends":["..."],"key_insights":["..."]}\n\n'
        "- patterns: recurring writing styles/techniques (4-8 items)\n"
        "- common_structures: shared structural/organizational patterns (4-8 items)\n"
        "- differentiators: unique angles per document, cite document name (4-8 items)\n"
        "- key_trends: market or research trends found across documents (4-8 items)\n"
        "- key_insights: the most actionable cross-document insights (4-8 items)",
    ),
    ("human", "Reports:\n\n{reports}"),
])

_AGGREGATE_BUDGET = 14_000


def _aggregate_analyses(doc_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    parts = []
    for da in doc_analyses:
        dtype = da.get("document_type", "book")
        chapters = "\n".join(f"  • {h}" for h in da.get("chapter_structure", [])) or "  (n/a)"
        trends_txt = "\n".join(f"  • {t}" for t in da.get("trends", [])) or "  (none)"
        insights_txt = "\n".join(f"  • {i}" for i in da.get("insights", [])) or "  (none)"
        frameworks_txt = "\n".join(f"  • {f}" for f in da.get("frameworks", [])) or "  (none)"

        parts.append(
            f"## {da['source']}  [{dtype.replace('_', ' ').title()}]\n"
            f"Pages: {da['page_count']} | Chunks: {da['chunk_count']}\n\n"
            f"### Summary\n{da.get('summary', '')}\n\n"
            f"### Key Insights\n{insights_txt}\n\n"
            f"### Frameworks / Models\n{frameworks_txt}\n\n"
            f"### Trends\n{trends_txt}\n\n"
            f"### Structure (Chapters / Sections)\n{chapters}"
        )

    combined = ("\n\n" + "─" * 60 + "\n\n").join(parts)[:_AGGREGATE_BUDGET]
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,
    )
    chain = _AGGREGATE_PROMPT | llm | StrOutputParser()
    try:
        raw = chain.invoke({"reports": combined}).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()
        parsed = json.loads(raw)
        for key in ("patterns", "common_structures", "differentiators", "key_trends", "key_insights"):
            parsed.setdefault(key, [])
        # Backward-compat alias
        parsed.setdefault("trends", parsed["key_trends"])
        return parsed
    except json.JSONDecodeError as exc:
        logger.error("Aggregation returned invalid JSON: %s", exc)
        return {
            "patterns": ["(Aggregation JSON error — see document_details)"],
            "common_structures": [], "differentiators": [],
            "key_trends": [], "key_insights": [], "trends": [],
        }
    except Exception as exc:
        logger.error("Aggregation LLM failed: %s", exc)
        return {
            "patterns": [f"(Aggregation failed: {exc})"],
            "common_structures": [], "differentiators": [],
            "key_trends": [], "key_insights": [], "trends": [],
        }


# ── Job management ────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _update_job(job_id: str, **kwargs: Any) -> None:
    if job_id in _JOB_STORE:
        _JOB_STORE[job_id].update(kwargs)


def create_job(
    file_data: List[Dict[str, Any]],
    mode: str,
    document_type: str = "book",
) -> str:
    job_id = str(uuid.uuid4())
    _JOB_STORE[job_id] = {
        "job_id":        job_id,
        "status":        "pending",
        "progress":      "Queued — waiting for analysis worker…",
        "mode":          mode,
        "document_type": document_type,
        "documents":     [f["filename"] for f in file_data],
        # Backward-compat alias
        "books":         [f["filename"] for f in file_data],
        "result":        None,
        "error":         None,
        "created_at":    _now(),
        "completed_at":  None,
    }
    logger.info(
        "Job %s created (mode=%s, doc_type=%s, %d files).",
        job_id, mode, document_type, len(file_data),
    )
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return _JOB_STORE.get(job_id)


def submit_analysis_job(
    job_id: str,
    file_data: List[Dict[str, Any]],
    mode: str,
    document_type: str = "book",
) -> None:
    _executor.submit(_run_analysis, job_id, file_data, mode, document_type)
    logger.info("Job %s submitted to executor (doc_type=%s).", job_id, document_type)


# ── Background worker ─────────────────────────────────────────────────────────

def _failed_entry(source: str, reason: str, document_type: str) -> Dict[str, Any]:
    return {
        "source":          source,
        "document_type":   document_type,
        "page_count":      0,
        "chunk_count":     0,
        "summary":         f"(Failed: {reason})",
        "insights":        [],
        "frameworks":      [],
        "trends":          [],
        "evidence":        [],
        "chapter_structure": [],
        # Backward-compat
        "writing_patterns": "",
    }


def _run_analysis(
    job_id: str,
    file_data: List[Dict[str, Any]],
    mode: str,
    document_type: str,
) -> None:
    try:
        _update_job(job_id, status="processing", progress="Initialising…")
        os.makedirs(settings.competitor_upload_dir, exist_ok=True)

        # Collection setup
        if mode == "replace":
            _update_job(job_id, progress="Clearing previous market data (replace mode)…")
            collection = _clear_and_recreate_collection()
            _delete_cache()
        else:
            _update_job(job_id, progress="Opening existing market collection (merge mode)…")
            collection = _get_market_collection()

        doc_analyses: List[Dict[str, Any]] = []
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
                doc_analyses.append(_failed_entry(fname, f"Save error: {exc}", document_type))
                continue

            # Parse
            try:
                pages = parse_file(save_path)
            except Exception as exc:
                doc_analyses.append(_failed_entry(fname, f"Parse error: {exc}", document_type))
                continue

            # Chunk
            chunks = chunk_documents(pages)
            logger.info("'%s': %d pages, %d chunks (type=%s)", fname, len(pages), len(chunks), document_type)

            # Embed + store
            _update_job(
                job_id,
                progress=f"[{idx}/{n}] Embedding {len(chunks)} chunks for '{fname}'…",
            )
            try:
                total_chunks += _store_market_chunks(collection, chunks, document_type)
            except Exception as exc:
                doc_analyses.append(_failed_entry(fname, f"Embedding error: {exc}", document_type))
                continue

            # Per-document LLM analysis
            _update_job(
                job_id,
                progress=f"[{idx}/{n}] LLM analysis of '{fname}' (document_type={document_type})…",
            )
            try:
                da = analyze_document(pages, chunks, fname, document_type)
            except Exception as exc:
                da = _failed_entry(fname, f"LLM error: {exc}", document_type)
                da.update({"page_count": len(pages), "chunk_count": len(chunks)})
            doc_analyses.append(da)

        # In merge mode, combine with previously cached document analyses
        prior_chunks_stored = 0
        if mode == "merge":
            existing = load_latest_cache()
            if existing:
                prior_chunks_stored = int(existing.get("chunks_stored") or 0)
                prior_details = existing.get("document_details") or []
                merged_by_source: Dict[str, Dict[str, Any]] = {}
                for da in prior_details:
                    if isinstance(da, dict) and da.get("source"):
                        merged_by_source[da["source"]] = da
                for da in doc_analyses:
                    merged_by_source[da["source"]] = da
                doc_analyses = list(merged_by_source.values())

        # Cross-document aggregation
        _update_job(
            job_id,
            progress=f"Cross-document aggregation across {len(doc_analyses)} documents…",
        )
        aggregated = _aggregate_analyses(doc_analyses)

        result: Dict[str, Any] = {
            # Enriched fields
            "document_type":    document_type,
            "key_trends":       aggregated.get("key_trends", []),
            "key_insights":     aggregated.get("key_insights", []),
            # Backward-compat fields
            "patterns":         aggregated.get("patterns", []),
            "common_structures":aggregated.get("common_structures", []),
            "differentiators":  aggregated.get("differentiators", []),
            "trends":           aggregated.get("key_trends", []),
            # Document details (unified name)
            "documents_analyzed": [da["source"] for da in doc_analyses],
            "document_details":   doc_analyses,
            # Backward-compat aliases
            "books_analyzed":   [da["source"] for da in doc_analyses],
            "book_details":     [
                {
                    "source":            da["source"],
                    "page_count":        da["page_count"],
                    "chunk_count":       da["chunk_count"],
                    "chapter_structure": da.get("chapter_structure", []),
                    "summary":           da.get("summary", ""),
                    "writing_patterns":  da.get("writing_patterns", ""),
                    "frameworks":        "\n".join(da.get("frameworks", [])),
                }
                for da in doc_analyses
            ],
            "chunks_stored":    prior_chunks_stored + total_chunks,
            "mode":             mode,
            "timestamp":        _now(),
        }
        _save_cache(result)
        _update_job(
            job_id,
            status="completed",
            progress="Analysis complete ✓",
            result=result,
            completed_at=_now(),
        )
        logger.info("Job %s completed.", job_id)

    except Exception as exc:
        logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
        _update_job(
            job_id,
            status="failed",
            progress="Analysis failed — see error field.",
            error=str(exc),
            completed_at=_now(),
        )


# ── Backward-compatible aliases (used by old competitor.py route) ─────────────

def submit_analysis_job_compat(
    job_id: str, file_data: List[Dict[str, Any]], mode: str
) -> None:
    """Backward-compatible wrapper — treats all files as 'book'."""
    submit_analysis_job(job_id, file_data, mode, document_type="book")
