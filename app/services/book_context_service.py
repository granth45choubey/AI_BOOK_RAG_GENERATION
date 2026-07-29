"""
Book Context Service — updated for flexible (partially optional) context.

Required at input : title, target_audience
Optional at input : subtitle, author_objective, reader_transformation,
                    initial_state, final_state, tone

When optional fields are omitted the LLM infers reasonable values from
the known fields before storage.  Backward compatibility is preserved:
old callers providing every field work identically to before.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.rag_pipeline.embedder import embed_documents
from app.rag_pipeline.retriever import get_collection
from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_BOOK_CTX_ID = "book_context_active"
_DOC_TYPE_TAG = "book_context"


# ── LLM inference for missing optional fields ─────────────────────────────────

def _infer_missing_fields(data: dict) -> dict:
    """
    Call the LLM once to fill in any empty optional fields.
    Only invoked when at least one optional field is blank.
    """
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_ollama import ChatOllama

    optional_keys = (
        "author_objective", "reader_transformation",
        "initial_state", "final_state", "tone",
    )
    missing = [k for k in optional_keys if not data.get(k)]
    if not missing:
        return data

    known_str  = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in data.items() if v and k not in missing
    )
    missing_str = ", ".join(m.replace("_", " ") for m in missing)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a book publishing consultant. "
            "Based on the provided book information, infer specific, tailored values "
            "for the missing fields. Never be generic. "
            "Return ONLY a valid JSON object with keys matching the missing field names.",
        ),
        (
            "human",
            f"Known information:\n{known_str}\n\n"
            f"Infer values for: {missing_str}\n\n"
            f'Return JSON like: {{"tone": "...", "author_objective": "..."}}',
        ),
    ])

    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.3,
    )
    chain = prompt | llm | StrOutputParser()

    try:
        raw = chain.invoke({}).strip()
        # Strip markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()

        inferred = json.loads(raw)
        for k, v in inferred.items():
            if k in data and not data[k]:
                data[k] = str(v)
        logger.info("LLM inferred missing book context fields: %s", list(inferred.keys()))

    except Exception as exc:
        logger.warning("LLM inference failed (%s) — using safe defaults.", exc)
        defaults = {
            "author_objective":      f"Help readers master the subject of '{data.get('title', 'this book')}'",
            "reader_transformation": "Gain practical knowledge and confidence in the subject",
            "initial_state":         "Curious beginner with limited prior knowledge",
            "final_state":           "Confident practitioner able to apply the material",
            "tone":                  "Clear, engaging, and accessible",
        }
        for k in missing:
            if not data.get(k):
                data[k] = defaults.get(k, "")

    return data


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_context_text(data: dict) -> str:
    lines = [f"Book Title: {data['title']}"]
    if data.get("subtitle"):
        lines.append(f"Subtitle: {data['subtitle']}")
    if data.get("target_audience"):
        lines.append(f"Target Audience: {data['target_audience']}")
    if data.get("author_objective"):
        lines.append(f"Author's Objective: {data['author_objective']}")
    if data.get("reader_transformation"):
        lines.append(f"Reader Transformation: {data['reader_transformation']}")
    if data.get("initial_state"):
        lines.append(f"Reader's Initial State (before reading): {data['initial_state']}")
    if data.get("final_state"):
        lines.append(f"Reader's Final State (after reading): {data['final_state']}")
    if data.get("tone"):
        lines.append(f"Tone & Style: {data['tone']}")
    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def create_book_context(
    title: str,
    target_audience: str,
    subtitle: Optional[str] = None,
    author_objective: Optional[str] = None,
    reader_transformation: Optional[str] = None,
    initial_state: Optional[str] = None,
    final_state: Optional[str] = None,
    tone: Optional[str] = None,
) -> dict:
    """
    Persist book context into ChromaDB as a high-priority document.

    Only ``title`` and ``target_audience`` are required.
    Missing optional fields are inferred by the LLM before storage.
    Calling again replaces the previous context (upsert semantics).
    """
    data = {
        "title":                 title,
        "subtitle":              subtitle or "",
        "target_audience":       target_audience,
        "author_objective":      author_objective or "",
        "reader_transformation": reader_transformation or "",
        "initial_state":         initial_state or "",
        "final_state":           final_state or "",
        "tone":                  tone or "",
    }

    needs_inference = any(
        not data[k]
        for k in ("author_objective", "reader_transformation",
                  "initial_state", "final_state", "tone")
    )
    if needs_inference:
        logger.info("Book context has missing optional fields — inferring via LLM.")
        data = _infer_missing_fields(data)

    context_text = _build_context_text(data)

    vector = embed_documents([context_text])[0]

    collection = get_collection()
    collection.upsert(
        ids=[_BOOK_CTX_ID],
        documents=[context_text],
        embeddings=[vector],
        metadatas=[{
            "doc_type":       _DOC_TYPE_TAG,
            "source_type":    "context",
            "priority_score": 0.95,
            "source":         "__book_context__",
            "page":           0,
            "chunk_index":    0,
            "raw_json":       json.dumps(data),
        }],
    )

    logger.info("Book context stored: '%s'", title)
    return {"context_text": context_text, **data}


def get_active_book_context() -> Optional[str]:
    """Fetch the active book context text. Returns None if not set."""
    collection = get_collection()
    try:
        result = collection.get(ids=[_BOOK_CTX_ID], include=["documents", "metadatas"])
    except Exception as exc:
        logger.warning("Could not fetch book context: %s", exc)
        return None
    docs = result.get("documents") or []
    return docs[0] if docs and docs[0] else None


def get_active_book_context_struct() -> Optional[dict]:
    """Fetch the full structured book context. Returns None if not set."""
    collection = get_collection()
    try:
        result = collection.get(ids=[_BOOK_CTX_ID], include=["documents", "metadatas"])
    except Exception as exc:
        logger.warning("Could not fetch book context struct: %s", exc)
        return None
    metas = result.get("metadatas") or []
    if not metas or not metas[0]:
        return None
    raw = metas[0].get("raw_json")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None
