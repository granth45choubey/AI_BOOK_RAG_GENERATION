"""
Market & Research Analysis Extractor.

Provides four specialized per-document analysis pipelines:

  book            — chapter structure, frameworks, writing style, positioning
  research_paper  — key findings, statistics, evidence, citations, trends
  industry_report — market trends, opportunities, challenges, future outlook
  whitepaper      — models, methodologies, strategic frameworks, recommendations

Each pipeline produces a normalized output dict:
  {
    source         : str,
    document_type  : str,
    page_count     : int,
    chunk_count    : int,
    summary        : str,
    insights       : List[str],
    frameworks     : List[str],
    trends         : List[str],
    evidence       : List[str],
    # type-specific extra fields also present
  }

All LLM calls are capped at _TEXT_BUDGET chars to stay within llama3.1:8b
context window.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_TEXT_BUDGET = 6_000   # chars per LLM call


# ── LLM helper ─────────────────────────────────────────────────────────────────

def _get_llm() -> ChatOllama:
    """Return a fresh (non-cached) LLM instance for thread-pool safety."""
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.2,
    )


def _call_llm(prompt: ChatPromptTemplate, variables: Dict[str, str]) -> str:
    chain = prompt | _get_llm() | StrOutputParser()
    try:
        return chain.invoke(variables).strip()
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return f"(LLM call failed: {exc})"


def _sample_text(chunks: List[Dict[str, Any]], start: int = 0, count: int = 15) -> str:
    sample = chunks[start: start + count]
    return "\n\n---\n\n".join(c["text"] for c in sample)[:_TEXT_BUDGET]


def _parse_json_list(raw: str, fallback_key: str = "items") -> List[str]:
    """Try to parse a JSON list from raw LLM output; fallback to line splitting."""
    raw = raw.strip()
    # Strip markdown fences
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(i) for i in parsed]
        if isinstance(parsed, dict):
            for key in (fallback_key, "items", "list", "results"):
                if key in parsed and isinstance(parsed[key], list):
                    return [str(i) for i in parsed[key]]
    except Exception:
        pass
    # Fallback: split on newlines or bullets
    lines = []
    for line in raw.splitlines():
        line = re.sub(r"^[\s\-•*\d.]+", "", line).strip()
        if line:
            lines.append(line)
    return lines[:10]


# ── Chapter detection (shared with existing extractor) ─────────────────────────

_CHAPTER_PATTERNS = [
    re.compile(r"^\s*(chapter|CHAPTER)\s+[\dIVXivx]+[\s:–—-]?.{0,60}$", re.MULTILINE),
    re.compile(r"^\s*\d{1,2}\.\s+[A-Z][A-Za-z\s]{3,60}$", re.MULTILINE),
    re.compile(r"^[A-Z][A-Z\s]{4,60}$", re.MULTILINE),
]
_MAX_CHAPTER_HEADINGS = 40


def _detect_chapters(pages: List[Dict[str, Any]]) -> List[str]:
    chapters: List[str] = []
    seen: set = set()
    for page in pages:
        text = page.get("text", "")
        for pat in _CHAPTER_PATTERNS:
            for m in pat.finditer(text):
                h = m.group().strip()
                if h and h not in seen and 4 < len(h) < 120 and not h.endswith("."):
                    chapters.append(h)
                    seen.add(h)
                    if len(chapters) >= _MAX_CHAPTER_HEADINGS:
                        return chapters
    return chapters


# ══════════════════════════════════════════════════════════════════════════════
# BOOK ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

_BOOK_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a literary analyst. "
        "Summarize what the following passages are about in 4–6 sentences. "
        "Focus on main themes, core argument, intended audience, and overall structure.",
    ),
    ("human", "Source: {source}\n\nPassages:\n{text}"),
])

_BOOK_FRAMEWORKS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Identify conceptual frameworks in this non-fiction book. "
        "Return a JSON array of strings (max 8 items), each describing one framework, "
        "step-model, named system, acronym, or core thesis found in the excerpts. "
        "No markdown fences. Example: [\"The 3-step process\", \"PARA method\"]",
    ),
    ("human", "Book: {source}\n\nExcerpts:\n{text}"),
])

_BOOK_PATTERNS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Analyze the writing style of this book. "
        "Return a JSON array of strings (max 6 items) covering: "
        "writing style, tone, point of view, use of examples, lists/frameworks density, sentence structure. "
        "No markdown fences.",
    ),
    ("human", "Book: {source}\n\nExcerpts:\n{text}"),
])


def analyze_book(
    pages: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    """Full book analysis pipeline."""
    logger.info("[market_extractor] Book analysis: '%s'", source)
    chapter_structure = _detect_chapters(pages)

    text_start = _sample_text(chunks, 0, 15)
    n = len(chunks)
    text_mid   = _sample_text(chunks, n // 2, 10)
    combined   = (text_start + "\n\n---\n\n" + text_mid)[:_TEXT_BUDGET]

    summary    = _call_llm(_BOOK_SUMMARY_PROMPT,    {"source": source, "text": text_start})
    frameworks = _parse_json_list(_call_llm(_BOOK_FRAMEWORKS_PROMPT, {"source": source, "text": combined}))
    insights   = _parse_json_list(_call_llm(_BOOK_PATTERNS_PROMPT,   {"source": source, "text": text_start}))

    return {
        "source":            source,
        "document_type":     "book",
        "page_count":        len(pages),
        "chunk_count":       len(chunks),
        "summary":           summary,
        "insights":          insights,       # writing style bullets
        "frameworks":        frameworks,
        "trends":            [],
        "evidence":          [],
        "chapter_structure": chapter_structure,
        "writing_patterns":  "\n".join(f"• {i}" for i in insights),
    }


# ══════════════════════════════════════════════════════════════════════════════
# RESEARCH PAPER ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

_RESEARCH_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a research analyst. "
        "Summarize the research paper below in 4–6 sentences covering: "
        "research question, methodology, key findings, and implications.",
    ),
    ("human", "Source: {source}\n\nPassages:\n{text}"),
])

_RESEARCH_FINDINGS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Extract key findings, statistics, evidence, and citations from this research paper. "
        "Return a JSON object with keys: "
        "\"findings\" (list of strings, max 8), "
        "\"statistics\" (list of strings with numbers, max 6), "
        "\"trends\" (list of strings, max 5). "
        "No markdown fences.",
    ),
    ("human", "Paper: {source}\n\nExcerpts:\n{text}"),
])

_RESEARCH_EVIDENCE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "List the strongest evidence statements, cited authors/studies, and "
        "methodological frameworks mentioned in this research paper. "
        "Return a JSON array of strings (max 8). No markdown fences.",
    ),
    ("human", "Paper: {source}\n\nExcerpts:\n{text}"),
])


def analyze_research_paper(
    pages: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    """Research paper analysis pipeline."""
    logger.info("[market_extractor] Research paper analysis: '%s'", source)
    text = _sample_text(chunks, 0, 20)

    summary = _call_llm(_RESEARCH_SUMMARY_PROMPT, {"source": source, "text": text})

    raw_findings = _call_llm(_RESEARCH_FINDINGS_PROMPT, {"source": source, "text": text})
    findings_obj: Dict[str, Any] = {}
    try:
        raw_clean = raw_findings.strip()
        if raw_clean.startswith("```"):
            raw_clean = raw_clean.split("```")[1].lstrip("json").strip()
        findings_obj = json.loads(raw_clean)
    except Exception:
        pass

    insights   = [str(x) for x in findings_obj.get("findings",   [])][:8]
    statistics = [str(x) for x in findings_obj.get("statistics", [])][:6]
    trends     = [str(x) for x in findings_obj.get("trends",     [])][:5]

    evidence   = _parse_json_list(_call_llm(_RESEARCH_EVIDENCE_PROMPT, {"source": source, "text": text}))

    return {
        "source":        source,
        "document_type": "research_paper",
        "page_count":    len(pages),
        "chunk_count":   len(chunks),
        "summary":       summary,
        "insights":      insights,
        "frameworks":    [],
        "trends":        trends,
        "evidence":      evidence,
        "statistics":    statistics,
    }


# ══════════════════════════════════════════════════════════════════════════════
# INDUSTRY REPORT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

_INDUSTRY_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a market analyst. "
        "Summarize this industry report in 4–6 sentences: "
        "market scope, key findings, market size/growth, and strategic implications.",
    ),
    ("human", "Source: {source}\n\nPassages:\n{text}"),
])

_INDUSTRY_TRENDS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Extract market intelligence from this industry report. "
        "Return a JSON object with keys: "
        "\"trends\" (list of market trends, max 8), "
        "\"opportunities\" (list of strings, max 5), "
        "\"challenges\" (list of strings, max 5), "
        "\"future_outlook\" (list of strings, max 4). "
        "No markdown fences.",
    ),
    ("human", "Report: {source}\n\nExcerpts:\n{text}"),
])

_INDUSTRY_EVIDENCE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Extract the most compelling data points, statistics, and market figures "
        "from this industry report. "
        "Return a JSON array of strings (max 8). No markdown fences.",
    ),
    ("human", "Report: {source}\n\nExcerpts:\n{text}"),
])


def analyze_industry_report(
    pages: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    """Industry report analysis pipeline."""
    logger.info("[market_extractor] Industry report analysis: '%s'", source)
    text = _sample_text(chunks, 0, 20)

    summary = _call_llm(_INDUSTRY_SUMMARY_PROMPT, {"source": source, "text": text})

    raw_trends = _call_llm(_INDUSTRY_TRENDS_PROMPT, {"source": source, "text": text})
    trends_obj: Dict[str, Any] = {}
    try:
        raw_clean = raw_trends.strip()
        if raw_clean.startswith("```"):
            raw_clean = raw_clean.split("```")[1].lstrip("json").strip()
        trends_obj = json.loads(raw_clean)
    except Exception:
        pass

    trends        = [str(x) for x in trends_obj.get("trends",         [])][:8]
    opportunities = [str(x) for x in trends_obj.get("opportunities",  [])][:5]
    challenges    = [str(x) for x in trends_obj.get("challenges",     [])][:5]
    future_outlook= [str(x) for x in trends_obj.get("future_outlook", [])][:4]

    evidence = _parse_json_list(_call_llm(_INDUSTRY_EVIDENCE_PROMPT, {"source": source, "text": text}))

    return {
        "source":         source,
        "document_type":  "industry_report",
        "page_count":     len(pages),
        "chunk_count":    len(chunks),
        "summary":        summary,
        "insights":       opportunities + challenges,
        "frameworks":     [],
        "trends":         trends,
        "evidence":       evidence,
        "opportunities":  opportunities,
        "challenges":     challenges,
        "future_outlook": future_outlook,
    }


# ══════════════════════════════════════════════════════════════════════════════
# WHITEPAPER ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

_WP_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a strategic analyst. "
        "Summarize this whitepaper in 4–6 sentences: "
        "problem addressed, proposed solution/model, methodology, and key recommendations.",
    ),
    ("human", "Source: {source}\n\nPassages:\n{text}"),
])

_WP_FRAMEWORKS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Identify models, methodologies, strategic frameworks, and recommendations "
        "proposed in this whitepaper. "
        "Return a JSON object with keys: "
        "\"frameworks\" (list of strings, max 6), "
        "\"methodologies\" (list of strings, max 4), "
        "\"recommendations\" (list of strings, max 6). "
        "No markdown fences.",
    ),
    ("human", "Whitepaper: {source}\n\nExcerpts:\n{text}"),
])

_WP_INSIGHTS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Extract the most actionable insights and strategic takeaways from this whitepaper. "
        "Return a JSON array of strings (max 8). No markdown fences.",
    ),
    ("human", "Whitepaper: {source}\n\nExcerpts:\n{text}"),
])


def analyze_whitepaper(
    pages: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    """Whitepaper analysis pipeline."""
    logger.info("[market_extractor] Whitepaper analysis: '%s'", source)
    text = _sample_text(chunks, 0, 20)

    summary = _call_llm(_WP_SUMMARY_PROMPT, {"source": source, "text": text})

    raw_fw = _call_llm(_WP_FRAMEWORKS_PROMPT, {"source": source, "text": text})
    fw_obj: Dict[str, Any] = {}
    try:
        raw_clean = raw_fw.strip()
        if raw_clean.startswith("```"):
            raw_clean = raw_clean.split("```")[1].lstrip("json").strip()
        fw_obj = json.loads(raw_clean)
    except Exception:
        pass

    frameworks      = [str(x) for x in fw_obj.get("frameworks",      [])][:6]
    methodologies   = [str(x) for x in fw_obj.get("methodologies",   [])][:4]
    recommendations = [str(x) for x in fw_obj.get("recommendations", [])][:6]

    insights = _parse_json_list(_call_llm(_WP_INSIGHTS_PROMPT, {"source": source, "text": text}))

    return {
        "source":          source,
        "document_type":   "whitepaper",
        "page_count":      len(pages),
        "chunk_count":     len(chunks),
        "summary":         summary,
        "insights":        insights,
        "frameworks":      frameworks,
        "trends":          [],
        "evidence":        [],
        "methodologies":   methodologies,
        "recommendations": recommendations,
    }


# ── Dispatch ───────────────────────────────────────────────────────────────────

_ANALYZERS = {
    "book":            analyze_book,
    "research_paper":  analyze_research_paper,
    "industry_report": analyze_industry_report,
    "whitepaper":      analyze_whitepaper,
}

VALID_DOCUMENT_TYPES = list(_ANALYZERS.keys())


def analyze_document(
    pages: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    source: str,
    document_type: str = "book",
) -> Dict[str, Any]:
    """
    Dispatch to the appropriate analysis pipeline based on document_type.

    Falls back to book analysis if an unknown document_type is supplied.
    """
    fn = _ANALYZERS.get(document_type, analyze_book)
    return fn(pages, chunks, source)
