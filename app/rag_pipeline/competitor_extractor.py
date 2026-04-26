"""
Competitor book analysis extractor.

Per-book pipeline
-----------------
1. Heuristic chapter structure detection (regex, no LLM — fast & deterministic).
2. LLM chunk summarization  — first N representative chunks.
3. LLM writing-pattern extraction — style, tone, POV, list density.
4. LLM framework/model extraction — recurring concepts, acronyms, step models.

All LLM calls are capped with a text budget (~6 000 chars) to stay within
the context window of llama3.1:8b running locally via Ollama.
"""
from __future__ import annotations

import re
import logging
from typing import List, Dict, Any

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Chapter heading heuristics ────────────────────────────────────────────────

_CHAPTER_PATTERNS = [
    # "Chapter 1", "CHAPTER 1", "Chapter I"
    re.compile(r"^\s*(chapter|CHAPTER)\s+[\dIVXivx]+[\s:–—-]?.{0,60}$", re.MULTILINE),
    # "1. Introduction", "12. Conclusion"
    re.compile(r"^\s*\d{1,2}\.\s+[A-Z][A-Za-z\s]{3,60}$", re.MULTILINE),
    # ALL-CAPS lines that look like section headers (3–8 words)
    re.compile(r"^[A-Z][A-Z\s]{4,60}$", re.MULTILINE),
]

_MAX_CHAPTER_HEADINGS = 40   # cap per book


def detect_chapters(pages: List[Dict[str, Any]]) -> List[str]:
    """
    Detect chapter / section headings from page texts using heuristics.

    Returns a deduplicated, ordered list of heading strings (max 40).
    """
    chapters: List[str] = []
    seen: set[str] = set()

    for page in pages:
        text = page.get("text", "")
        for pattern in _CHAPTER_PATTERNS:
            for match in pattern.finditer(text):
                heading = match.group().strip()
                # Filter out noise: too short, looks like a sentence, or duplicate
                if (
                    heading
                    and heading not in seen
                    and 4 < len(heading) < 120
                    and not heading.endswith(".")  # sentences end with periods
                ):
                    chapters.append(heading)
                    seen.add(heading)
                    if len(chapters) >= _MAX_CHAPTER_HEADINGS:
                        return chapters
    return chapters


# ── LLM setup ─────────────────────────────────────────────────────────────────

_TEXT_BUDGET = 6_000   # chars fed to each LLM call


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
        return chain.invoke(variables)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return f"(LLM call failed: {exc})"


# ── Prompts ───────────────────────────────────────────────────────────────────

_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a literary analyst. "
        "Summarize what the following text passages are about in 4–6 sentences. "
        "Focus on the main themes, core argument, intended audience, and overall structure of the book.",
    ),
    ("human", "Source: {source}\n\nPassages:\n{text}"),
])

_PATTERN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a book writing analyst. Analyze the excerpts below and identify:\n"
        "1. Writing style (formal / casual / conversational / academic)\n"
        "2. Tone (authoritative / friendly / inspiring / neutral / humorous)\n"
        "3. Point of view (1st person / 2nd person / 3rd person)\n"
        "4. Use of examples (heavy / moderate / sparse)\n"
        "5. Use of lists and frameworks (heavy / moderate / sparse)\n"
        "6. Sentence structure (short & punchy / long & complex / mixed)\n\n"
        "Return a concise bullet-point analysis, one bullet per category.",
    ),
    ("human", "Book: {source}\n\nExcerpts:\n{text}"),
])

_FRAMEWORK_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert at identifying conceptual frameworks in non-fiction books. "
        "Analyze the excerpts below and identify:\n"
        "1. Recurring frameworks or step-based models (e.g. 'The 3-step process', 'PARA method')\n"
        "2. Named systems, acronyms, or coined terms\n"
        "3. Repeated metaphors or analogies\n"
        "4. Core thesis or central argument\n\n"
        "Return a concise bullet-point list. "
        "If nothing notable is found, say 'No distinctive frameworks detected.'",
    ),
    ("human", "Book: {source}\n\nExcerpts:\n{text}"),
])


# ── Per-book public API ───────────────────────────────────────────────────────

def _sample_text(chunks: List[Dict[str, Any]], sample_start: int, sample_size: int) -> str:
    """Join a slice of chunks into a single string, capped at _TEXT_BUDGET chars."""
    sampled = chunks[sample_start : sample_start + sample_size]
    return "\n\n---\n\n".join(c["text"] for c in sampled)[:_TEXT_BUDGET]


def summarize_chunks(chunks: List[Dict[str, Any]], source: str) -> str:
    """Summarize the first ~15 chunks (intro / early chapters carry most context)."""
    text = _sample_text(chunks, 0, 15)
    return _call_llm(_SUMMARY_PROMPT, {"source": source, "text": text})


def extract_patterns(chunks: List[Dict[str, Any]], source: str) -> str:
    """Extract writing-style patterns from the first ~20 chunks."""
    text = _sample_text(chunks, 0, 20)
    return _call_llm(_PATTERN_PROMPT, {"source": source, "text": text})


def extract_frameworks(chunks: List[Dict[str, Any]], source: str) -> str:
    """
    Extract repeated frameworks / models.
    Samples from both the beginning and the middle of the book for breadth.
    """
    n = len(chunks)
    mid = n // 2
    start_text = _sample_text(chunks, 0, 10)
    mid_text   = _sample_text(chunks, mid, 10)
    combined   = (start_text + "\n\n---\n\n" + mid_text)[:_TEXT_BUDGET]
    return _call_llm(_FRAMEWORK_PROMPT, {"source": source, "text": combined})


def analyze_book(
    pages: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    """
    Full per-book analysis.

    Parameters
    ----------
    pages   : list of page dicts (text, source, page)
    chunks  : list of chunk dicts (text, source, page, chunk_index)
    source  : filename / book identifier

    Returns
    -------
    Dict with: source, page_count, chunk_count, chapter_structure,
               summary, writing_patterns, frameworks
    """
    logger.info("[competitor_extractor] Detecting chapters for '%s'…", source)
    chapters = detect_chapters(pages)

    logger.info("[competitor_extractor] Summarizing chunks for '%s'…", source)
    summary = summarize_chunks(chunks, source)

    logger.info("[competitor_extractor] Extracting writing patterns for '%s'…", source)
    patterns = extract_patterns(chunks, source)

    logger.info("[competitor_extractor] Extracting frameworks for '%s'…", source)
    frameworks = extract_frameworks(chunks, source)

    return {
        "source":            source,
        "page_count":        len(pages),
        "chunk_count":       len(chunks),
        "chapter_structure": chapters,
        "summary":           summary,
        "writing_patterns":  patterns,
        "frameworks":        frameworks,
    }
