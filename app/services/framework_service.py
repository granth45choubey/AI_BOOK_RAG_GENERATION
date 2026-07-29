"""
Framework Generator Agent Service.

Generates 3 distinct book frameworks from:
  - Book context (title, audience, transformation)
  - Competitor analysis cache
  - Retrieved RAG docs (lightweight retrieval)

Each framework contains:
  - framework_id   : stable slug
  - name           : short title
  - unique_angle   : differentiating philosophy / hook
  - flow_of_transformation : reader journey arc (before → after)
  - chapter_breakdown : list of chapter dicts {number, title, purpose, key_concepts}

State:
  - ACTIVE_FRAMEWORKS : last generated set (in-memory + disk cache)
  - SELECTED_FRAMEWORK: currently selected framework (persisted to disk)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.services.book_context_service import get_active_book_context_struct
from app.services.competitor_service import load_latest_cache
from app.rag_pipeline.retriever import retrieve_for_framework
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── In-memory state ────────────────────────────────────────────────────────────
ACTIVE_FRAMEWORKS: List[Dict[str, Any]] = []

# ── Persistence paths ────────────────────────────────────────────────────────────
_STORE_PATH = Path(settings.author_upload_dir) / "selected_framework.json"
_CACHE_PATH = Path(settings.author_upload_dir) / "generated_frameworks_cache.json"


# ── LLM prompt (condensed system message — same output schema) ────────────────

_FRAMEWORK_SYSTEM = """\
You are an expert book architect. Design THREE distinct book frameworks as ONE JSON array only.
No markdown fences. No commentary. Exactly 3 objects with keys:
framework_id, name, unique_angle, flow_of_transformation {{before,journey,after}},
chapter_breakdown [{{number, title, purpose, key_concepts[]}}].

Rules: 6-12 chapters each; frameworks must differ in structure and angle; ground in inputs provided.
"""

_FRAMEWORK_HUMAN = """\
## Book Context
{book_context}

## Market / Competitor Analysis
{competitor_analysis}

## Retrieved Knowledge (excerpts)
{rag_docs}

Return ONLY the JSON array of 3 frameworks.
"""

_FRAMEWORK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _FRAMEWORK_SYSTEM),
    ("human",  _FRAMEWORK_HUMAN),
])


# ── LLM (cached singleton) ────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.4,
        num_predict=settings.llm_num_predict_framework,
    )


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _inputs_fingerprint(
    book_context_override: Optional[Dict[str, Any]],
    competitor_analysis_override: Optional[Dict[str, Any]],
) -> str:
    """Hash of inputs that drive framework generation (for cache lookup)."""
    ctx = book_context_override or get_active_book_context_struct() or {}
    cache = competitor_analysis_override or load_latest_cache() or {}
    payload = json.dumps(
        {
            "book_context": ctx,
            "cache_timestamp": cache.get("timestamp"),
            "patterns": cache.get("patterns", [])[:8],
            "common_structures": cache.get("common_structures", [])[:8],
            "differentiators": cache.get("differentiators", [])[:8],
            "key_insights": cache.get("key_insights", [])[:8],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _load_framework_cache() -> Optional[Dict[str, Any]]:
    try:
        if _CACHE_PATH.exists():
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Cannot read framework cache: %s", exc)
    return None


def _save_framework_cache(fingerprint: str, frameworks: List[Dict[str, Any]]) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps(
                {
                    "inputs_fingerprint": fingerprint,
                    "frameworks": frameworks,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Cannot write framework cache: %s", exc)


def _restore_frameworks_from_cache() -> bool:
    """Load ACTIVE_FRAMEWORKS from disk cache if memory is empty."""
    global ACTIVE_FRAMEWORKS
    if ACTIVE_FRAMEWORKS:
        return True
    cached = _load_framework_cache()
    if cached and cached.get("frameworks"):
        ACTIVE_FRAMEWORKS = cached["frameworks"]
        return True
    return False


# ── Input builders ─────────────────────────────────────────────────────────────

def _build_book_context_section(override: Optional[Dict[str, Any]]) -> str:
    """Return a human-readable book context string."""
    data = override or get_active_book_context_struct()
    if not data:
        return "(No book context set.)"
    lines = []
    for key, label in [
        ("title",                "Title"),
        ("subtitle",             "Subtitle"),
        ("target_audience",      "Target Audience"),
        ("author_objective",     "Author Objective"),
        ("reader_transformation","Reader Transformation"),
        ("initial_state",        "Reader Before"),
        ("final_state",          "Reader After"),
        ("tone",                 "Tone & Style"),
    ]:
        val = data.get(key, "")
        if val:
            lines.append(f"- {label}: {val}")
    return "\n".join(lines) if lines else "(Book context fields are empty.)"


def _build_competitor_section(override: Optional[Dict[str, Any]]) -> str:
    """Return a condensed market/competitor analysis string (cached JSON — no re-analysis)."""
    cache = override or load_latest_cache()
    if not cache:
        return "(No market analysis available.)"
    parts = []
    for key, label, limit in (
        ("patterns",          "Patterns", 5),
        ("common_structures", "Structures", 5),
        ("differentiators",   "Differentiators", 5),
        ("key_insights",      "Key Insights", 4),
        ("key_trends",        "Key Trends", 4),
    ):
        items = cache.get(key, [])
        if items:
            parts.append(f"{label}:\n" + "\n".join(f"  • {p}" for p in items[:limit]))
    return "\n\n".join(parts) if parts else "(Market cache is empty.)"


def _build_rag_section(query: str, override: Optional[List[Dict[str, Any]]]) -> str:
    """Return a compact RAG retrieval section for framework prompts."""
    max_chars = settings.generation_chunk_max_chars
    if override is not None:
        chunks = override
    else:
        try:
            chunks = retrieve_for_framework(query)
        except Exception as exc:
            logger.warning("RAG retrieval failed during framework gen: %s", exc)
            chunks = []

    if not chunks:
        return "(No relevant documents retrieved.)"

    lines = []
    for i, c in enumerate(chunks, 1):
        text = c["text"][:max_chars]
        if len(c["text"]) > max_chars:
            text += "…"
        lines.append(
            f"[{i}] {text}\n"
            f"    (Source: {c.get('source','?')}, Page {c.get('page','?')})"
        )
    return "\n\n".join(lines)


# ── JSON extraction helpers ────────────────────────────────────────────────────

def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 1)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")].strip()
    return raw


def _extract_json_array(raw: str) -> List[Dict[str, Any]]:
    """
    Try to extract the first JSON array from the LLM response.
    Falls back to regex extraction if the response has extra text.
    """
    cleaned = _strip_fences(raw)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\[[\s\S]+\])", cleaned)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON array from LLM output:\n{raw[:500]}")


def _validate_framework(fw: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """Ensure each framework dict has all required keys; fill defaults if missing."""
    fw.setdefault("framework_id", f"framework_{chr(97 + idx)}")
    fw.setdefault("name", f"Framework {chr(65 + idx)}")
    fw.setdefault("unique_angle", "Not specified.")
    fw.setdefault("flow_of_transformation", {
        "before": "Reader lacks knowledge.",
        "journey": "Guided step-by-step through the material.",
        "after": "Reader gains mastery.",
    })
    fot = fw["flow_of_transformation"]
    if not isinstance(fot, dict):
        fw["flow_of_transformation"] = {"before": str(fot), "journey": "", "after": ""}
    fw.setdefault("chapter_breakdown", [])
    chapters = fw["chapter_breakdown"]
    validated_chapters = []
    for j, ch in enumerate(chapters):
        if not isinstance(ch, dict):
            continue
        ch.setdefault("number", j + 1)
        ch.setdefault("title", f"Chapter {j + 1}")
        ch.setdefault("purpose", "")
        ch.setdefault("key_concepts", [])
        validated_chapters.append(ch)
    fw["chapter_breakdown"] = validated_chapters
    return fw


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_frameworks(
    book_context_override: Optional[Dict[str, Any]] = None,
    competitor_analysis_override: Optional[Dict[str, Any]] = None,
    retrieved_docs_override: Optional[List[Dict[str, Any]]] = None,
    force_regenerate: bool = False,
) -> List[Dict[str, Any]]:
    """
    Generate 3 book frameworks using LLM.

    When ``force_regenerate`` is False and inputs are unchanged, returns cached
    frameworks from disk without calling the LLM.
    """
    global ACTIVE_FRAMEWORKS

    fingerprint = _inputs_fingerprint(book_context_override, competitor_analysis_override)
    has_overrides = any([
        book_context_override,
        competitor_analysis_override,
        retrieved_docs_override is not None,
    ])

    if (
        settings.framework_cache_enabled
        and not force_regenerate
        and not has_overrides
    ):
        cached = _load_framework_cache()
        if cached and cached.get("inputs_fingerprint") == fingerprint:
            ACTIVE_FRAMEWORKS = cached["frameworks"]
            logger.info(
                "Returning cached frameworks (fingerprint=%s, count=%d).",
                fingerprint, len(ACTIVE_FRAMEWORKS),
            )
            return ACTIVE_FRAMEWORKS

    ctx_data = book_context_override or get_active_book_context_struct()
    rag_query = (
        f"book structure frameworks for {ctx_data.get('title', 'this book')} "
        f"targeting {ctx_data.get('target_audience', 'general readers')}"
        if ctx_data else "book framework structure chapter outline"
    )

    book_ctx_str   = _build_book_context_section(book_context_override)
    competitor_str = _build_competitor_section(competitor_analysis_override)
    rag_str        = _build_rag_section(rag_query, retrieved_docs_override)

    logger.info("Generating 3 book frameworks via LLM (prompt ~%d chars)…",
                len(book_ctx_str) + len(competitor_str) + len(rag_str))
    chain = _FRAMEWORK_PROMPT | _get_llm() | StrOutputParser()
    raw = chain.invoke({
        "book_context":        book_ctx_str,
        "competitor_analysis": competitor_str,
        "rag_docs":            rag_str,
    })

    frameworks = _extract_json_array(raw)
    if len(frameworks) < 3:
        logger.warning("LLM returned %d frameworks (expected 3) — padding.", len(frameworks))
        while len(frameworks) < 3:
            frameworks.append({})

    validated = [_validate_framework(fw, i) for i, fw in enumerate(frameworks[:3])]
    ACTIVE_FRAMEWORKS = validated

    if settings.framework_cache_enabled and not has_overrides:
        _save_framework_cache(fingerprint, validated)

    logger.info("Framework generation complete: %s", [f["name"] for f in validated])
    return validated


def get_active_frameworks() -> List[Dict[str, Any]]:
    """Return the last generated frameworks (memory or disk cache)."""
    _restore_frameworks_from_cache()
    return ACTIVE_FRAMEWORKS


# ── Framework selection ────────────────────────────────────────────────────────

def select_framework(framework_id: str) -> Dict[str, Any]:
    """
    Mark a framework as selected and persist it to disk.

    Raises ValueError if framework_id is not found in ACTIVE_FRAMEWORKS.
    """
    global ACTIVE_FRAMEWORKS

    if not ACTIVE_FRAMEWORKS:
        _restore_frameworks_from_cache()

    if not ACTIVE_FRAMEWORKS:
        saved = load_selected_framework()
        if saved and saved.get("framework_id") == framework_id:
            return {**saved, "selected": True}
        raise ValueError(
            "No frameworks have been generated yet. "
            "Call POST /generate-frameworks first."
        )

    match = next(
        (f for f in ACTIVE_FRAMEWORKS if f["framework_id"] == framework_id),
        None,
    )
    if match is None:
        available = [f["framework_id"] for f in ACTIVE_FRAMEWORKS]
        raise ValueError(
            f"framework_id '{framework_id}' not found. "
            f"Available: {available}"
        )

    result = {**match, "selected": True}
    _persist_selected(result)
    logger.info("Framework selected: %s ('%s')", framework_id, match["name"])
    return result


def load_selected_framework() -> Optional[Dict[str, Any]]:
    """Load the persisted selected framework from disk."""
    try:
        if _STORE_PATH.exists():
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Cannot read selected framework: %s", exc)
    return None


def _persist_selected(framework: Dict[str, Any]) -> None:
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STORE_PATH.write_text(
            json.dumps(framework, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Selected framework saved to %s", _STORE_PATH)
    except Exception as exc:
        logger.warning("Could not persist selected framework: %s", exc)
