"""Profile framework generation and structured chapter generation pipelines."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag_pipeline.retriever import retrieve_layered
from app.services.framework_service import (
    _build_book_context_section,
    _build_competitor_section,
    _build_rag_section,
    generate_frameworks,
)
from app.rag_pipeline.generator import generate_answer_structured
from app.services.book_context_service import get_active_book_context_struct


def _section(name: str, fn):
    t0 = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - t0
    size = len(result) if isinstance(result, str) else len(str(result))
    print(f"  {name}: {elapsed:.3f}s (output ~{size:,} chars)")
    return elapsed, result


def profile_framework():
    print("\n=== Framework Generation Pipeline ===")
    totals = {"retrieval": 0, "prompt": 0, "llm": 0, "parse": 0, "save": 0}

    ctx_data = get_active_book_context_struct()
    rag_query = (
        f"book structure frameworks for {ctx_data.get('title', 'this book')} "
        f"targeting {ctx_data.get('target_audience', 'general readers')}"
        if ctx_data
        else "book framework structure chapter outline"
    )

    t0 = time.perf_counter()
    retrieve_layered(rag_query)
    totals["retrieval"] += time.perf_counter() - t0

    t0 = time.perf_counter()
    book_ctx = _build_book_context_section(None)
    comp = _build_competitor_section(None)
    rag = _build_rag_section(rag_query, None)
    prompt_size = len(book_ctx) + len(comp) + len(rag)
    totals["prompt"] += time.perf_counter() - t0
    print(f"  prompt assembly: {totals['prompt']:.3f}s (~{prompt_size:,} chars total sections)")

    print("  Running full generate_frameworks() …")
    t0 = time.perf_counter()
    try:
        fws = generate_frameworks()
        llm_total = time.perf_counter() - t0
        totals["llm"] = llm_total  # includes retrieval+prompt inside
        print(f"  generate_frameworks TOTAL: {llm_total:.1f}s ({len(fws)} frameworks)")
    except Exception as exc:
        print(f"  generate_frameworks FAILED: {exc}")
        llm_total = time.perf_counter() - t0

    return totals


def profile_chapter_query(question: str = "Write Chapter 1 introduction for the book."):
    print(f"\n=== Structured Chapter Generation (/query path) ===")
    print(f"Question: {question[:80]}…")

    t0 = time.perf_counter()
    ctx = retrieve_layered(question)
    t_ret = time.perf_counter() - t0
    print(f"  retrieval: {t_ret:.3f}s")

    t0 = time.perf_counter()
    from app.rag_pipeline.generator import (
        _build_author_guidance_section,
        _build_framework_section,
        _fmt_chunks,
    )
    sections = [
        _build_author_guidance_section(ctx),
        _build_framework_section(),
        _fmt_chunks(ctx.author_chunks, "author"),
        ctx.book_context_text or "",
        ctx.outline_text or "",
        _fmt_chunks(ctx.research_chunks, "research"),
        _fmt_chunks(ctx.industry_chunks, "industry"),
        _fmt_chunks(ctx.whitepaper_chunks, "whitepaper"),
        _fmt_chunks(ctx.competitor_chunks, "competitor"),
        _fmt_chunks(ctx.general_chunks, "general"),
    ]
    prompt_chars = sum(len(s) for s in sections)
    t_prompt = time.perf_counter() - t0
    print(f"  prompt build: {t_prompt:.3f}s (~{prompt_chars:,} chars)")

    t0 = time.perf_counter()
    try:
        answer = generate_answer_structured(question, ctx)
        t_llm = time.perf_counter() - t0
        print(f"  LLM generation: {t_llm:.1f}s (answer ~{len(answer):,} chars)")
    except Exception as exc:
        t_llm = time.perf_counter() - t0
        print(f"  LLM FAILED ({t_llm:.1f}s): {exc}")


if __name__ == "__main__":
    profile_framework()
    profile_chapter_query()
