"""
Answer generation module.

Uses LangChain's ChatOllama to produce answers grounded in retrieved context.
Two prompt modes:
  1. Standard RAG  — generic Q&A grounded in retrieved passages.
  2. Book-context  — author-mode generation aligned with the active book's
                     goals, audience, and tone.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Prompts ───────────────────────────────────────────────────────────────────

# --- Standard RAG prompt (no book context) ---
_SYSTEM_PROMPT = """\
You are a knowledgeable and helpful RAG assistant.
You are given numbered context passages extracted from user-uploaded documents.
Your job is to answer the user's question by synthesizing information from those passages.

Guidelines:
- Read ALL context passages carefully before answering.
- Provide a thorough, well-structured answer using the information found in the context.
- If the context has partial information, use it and clearly state what you found.
- Cite sources in-line using the format: (Source: <filename>, Page <N>).
- Use bullet points or numbered lists when presenting multiple facts or steps.
- Only say "I cannot find this information in the provided documents" if NONE of the
  context passages contain ANY relevant content. Do NOT refuse prematurely.
- Do NOT fabricate any information that is not present in the context.
"""

_HUMAN_TEMPLATE = """\
## Retrieved Context Passages

{context}

---

## User Question

{question}

## Answer (based strictly on the context above)
"""

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", _HUMAN_TEMPLATE),
])

# --- Book-context-aware prompt ---
_BOOK_SYSTEM_TEMPLATE = """\
You are writing a book with this context:

{book_context}

Use the retrieved knowledge passages below together with the book context above
to craft content that is perfectly aligned with the book's goals, audience, and tone.

Guidelines:
- Always keep the target audience and tone in mind.
- Draw on the retrieved passages for factual grounding.
- Cite sources in-line using the format: (Source: <filename>, Page <N>).
- Structure the response to serve as polished, ready-to-use book content.
- Do NOT fabricate any information that is not present in the context.
"""

_BOOK_HUMAN_TEMPLATE = """\
## Retrieved Knowledge Passages

{context}

---

## Writing Task / Question

{question}

## Book Content (grounded in context, aligned with book goals)
"""

# _BOOK_PROMPT is built dynamically because the system message carries
# book_context as a variable — we use a plain format-string approach.
_BOOK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _BOOK_SYSTEM_TEMPLATE),
    ("human", _BOOK_HUMAN_TEMPLATE),
])


# ── LLM ───────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_llm() -> ChatOllama:
    logger.info("LLM: Ollama | model: %s | url: %s", settings.ollama_model, settings.ollama_base_url)
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.3,
        num_predict=settings.llm_num_predict_generation,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def generate_answer(
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    book_context: Optional[str] = None,
) -> str:
    """
    Generate an answer from retrieved chunks.

    Parameters
    ----------
    question        : the user's question / writing task
    retrieved_chunks: list of dicts returned by retriever.retrieve_chunks()
    book_context    : optional book context string; when provided the LLM
                      switches to author-mode generation.

    Returns
    -------
    Answer / content string from the LLM.
    """
    if not retrieved_chunks:
        if not book_context:
            return ("No relevant documents were found in the knowledge base. "
                    "Please make sure you have uploaded and ingested documents first.")
        # With book context we can still respond even without retrieved chunks
        logger.warning("No retrieved chunks — generating from book context only.")

    # Format context with clear source attribution and separators
    context_parts: List[str] = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        header = (
            f"--- Passage [{i}] ---\n"
            f"Source: {chunk['source']} | Page: {chunk['page']} "
            f"| Chunk #{chunk['chunk_index']} | Relevance: {chunk['score']:.3f}"
        )
        context_parts.append(f"{header}\n\n{chunk['text']}")

    context = "\n\n".join(context_parts) if context_parts else "(No retrieved passages available.)"

    # ── Choose prompt based on whether a book context is active ───────────────
    if book_context:
        chain = _BOOK_PROMPT | _get_llm() | StrOutputParser()
        invoke_payload = {
            "book_context": book_context,
            "context": context,
            "question": question,
        }
        logger.info(
            "[Book-Context Mode] Generating answer for: %.60s…", question
        )
    else:
        chain = _PROMPT | _get_llm() | StrOutputParser()
        invoke_payload = {"context": context, "question": question}
        logger.info("Generated answer for question: %.60s…", question)

    try:
        answer = chain.invoke(invoke_payload)
        return answer
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        raise


# ── Priority-based structured generation ──────────────────────────────────────────────────

_STRUCTURED_SYSTEM = """\
You are an AI book writing assistant.

Follow these priorities STRICTLY:
1. Author guidance and author-provided documents (highest priority)
2. Selected book framework (when provided — align structure and angle)
3. Book context (title, audience, transformation)
4. Chapter outline (if provided — MUST be followed exactly)
5. Research paper evidence
6. Industry report insights
7. Whitepaper frameworks and recommendations
8. Competitor book insights (differentiation reference only)
9. General retrieved knowledge base

Guidelines:
- Do NOT generate generic content.
- Maintain consistency with the author's intent and voice.
- Cite sources in-line using (Source: <filename>, Page <N>).
- Never fabricate information not present in the provided context.

{outline_instruction}
"""

# Injected into {outline_instruction} based on whether an outline is active
_OUTLINE_STRICT = """\
OUTLINE RULES (outline is ACTIVE — enforce strictly):
- Follow the chapter order EXACTLY as listed in the Chapter Outline section.
- Follow the section order within each chapter EXACTLY as listed.
- Do NOT invent, add, rename, merge, or reorder any chapters or sections.
- Every piece of content you write must fit within the existing chapter/section structure.
- If asked to write a specific chapter or section, produce content only for that chapter/section."""

_OUTLINE_ABSENT = """\
OUTLINE RULES (no outline set — free generation):
- Generate a logical chapter and section structure appropriate for the book context.
- Base structure on author documents, book context, and retrieved knowledge."""

_STRUCTURED_HUMAN = """\
## Writing Task / Question
{question}

---
{author_guidance_section}{framework_section}{author_section}{book_context_section}{outline_section}{research_section}{industry_section}{whitepaper_section}{competitor_section}{general_section}
## Response (aligned with author intent and book context)
"""

_STRUCTURED_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _STRUCTURED_SYSTEM),
    ("human",  _STRUCTURED_HUMAN),
])


def _fmt_chunks(
    chunks: List[Dict[str, Any]],
    label: str,
    max_chars: int | None = None,
) -> str:
    """Format retrieved chunks into a labeled section (truncated for prompt size)."""
    if not chunks:
        return ""
    limit = max_chars or settings.generation_chunk_max_chars
    lines = [f"## {label}\n"]
    for i, c in enumerate(chunks, 1):
        text = c["text"]
        if len(text) > limit:
            text = text[:limit] + "…"
        lines.append(
            f"[{i}] {text}\n"
            f"    (Source: {c['source']}, Page {c.get('page', '?')})"
        )
    return "\n".join(lines) + "\n\n"


def _build_author_guidance_section(ctx: "StructuredContext") -> str:  # noqa: F821
    """Combine persisted author guidelines with per-chunk description metadata."""
    from app.services.author_service import get_aggregated_author_descriptions

    parts: List[str] = []
    aggregated = get_aggregated_author_descriptions()
    if aggregated:
        parts.append(aggregated)

    seen: set = set()
    for chunk in ctx.author_chunks:
        desc = (chunk.get("author_description") or "").strip()
        if desc and desc not in seen:
            parts.append(desc)
            seen.add(desc)

    if not parts:
        return ""
    return "## Author Guidance (Highest Priority)\n" + "\n\n".join(parts) + "\n\n"


def _build_framework_section() -> str:
    """Compact selected-framework summary for chapter generation prompts."""
    from app.services.framework_service import load_selected_framework

    fw = load_selected_framework()
    if not fw:
        return ""

    lines = [
        "## Selected Book Framework",
        f"Name: {fw.get('name', 'Unnamed')}",
        f"Angle: {fw.get('unique_angle', '')}",
    ]
    fot = fw.get("flow_of_transformation") or {}
    if isinstance(fot, dict):
        before = fot.get("before", "")
        after = fot.get("after", "")
        if before or after:
            lines.append(f"Reader arc: {before} → {after}")

    chapters = fw.get("chapter_breakdown") or []
    if chapters:
        titles = [
            f"{ch.get('number', '?')}. {ch.get('title', 'Untitled')}"
            for ch in chapters[:12]
        ]
        lines.append("Chapters: " + " | ".join(titles))

    return "\n".join(lines) + "\n\n"


def generate_answer_structured(question: str, ctx: "StructuredContext") -> str:  # noqa: F821
    """
    Generate an answer using the priority-ordered StructuredContext.

    Priority order in the prompt:
      author docs → book context → outline → competitor insights → general knowledge

    If an outline is present the LLM is instructed to:
      - Follow chapter order exactly
      - Follow section order within each chapter exactly
      - Not invent additional chapters or sections

    If no outline is present the LLM generates structure freely.

    Falls back gracefully when any layer is empty.
    """
    from app.rag_pipeline.retriever import StructuredContext  # local import avoids circular dep

    outline_active = bool(ctx.outline_text)

    author_guidance_section = _build_author_guidance_section(ctx)
    framework_section       = _build_framework_section()
    author_section          = _fmt_chunks(ctx.author_chunks, "Author-Provided Content")
    book_context_section = f"## Book Context\n{ctx.book_context_text}\n\n" if ctx.book_context_text else ""
    outline_section      = (
        f"## Chapter Outline (Follow Strictly — do NOT alter chapter/section order)\n"
        f"{ctx.outline_text}\n\n"
        if outline_active else ""
    )
    # Market & Research Analysis layers
    research_section     = _fmt_chunks(
        ctx.research_chunks,
        "Research Paper Evidence (Empirical Grounding — cite statistics and findings)",
    )
    industry_section     = _fmt_chunks(
        ctx.industry_chunks,
        "Industry Report Insights (Market Trends, Opportunities, Challenges)",
    )
    whitepaper_section   = _fmt_chunks(
        ctx.whitepaper_chunks,
        "Whitepaper Frameworks & Recommendations (Strategic Methodologies)",
    )
    competitor_section   = _fmt_chunks(ctx.competitor_chunks, "Competitor Book Insights (Differentiation Reference Only)")
    general_section      = _fmt_chunks(ctx.general_chunks,    "Retrieved Knowledge Base")

    has_any = any([
        author_guidance_section,
        framework_section,
        ctx.author_chunks,
        ctx.book_context_text,
        ctx.outline_text,
        ctx.research_chunks,
        ctx.industry_chunks,
        ctx.whitepaper_chunks,
        ctx.competitor_chunks,
        ctx.general_chunks,
    ])
    if not has_any:
        return (
            "No relevant context found in the knowledge base. "
            "Please upload documents or set a book context first."
        )

    outline_instruction = _OUTLINE_STRICT if outline_active else _OUTLINE_ABSENT

    if outline_active:
        logger.info(
            "[Structured Gen] Outline ACTIVE — strict chapter/section ordering enforced."
        )
    else:
        logger.info(
            "[Structured Gen] No outline — free generation mode."
        )

    chain = _STRUCTURED_PROMPT | _get_llm() | StrOutputParser()
    try:
        return chain.invoke({
            "question":               question,
            "outline_instruction":    outline_instruction,
            "author_guidance_section": author_guidance_section,
            "framework_section":      framework_section,
            "author_section":         author_section,
            "book_context_section":   book_context_section,
            "outline_section":        outline_section,
            "research_section":       research_section,
            "industry_section":       industry_section,
            "whitepaper_section":     whitepaper_section,
            "competitor_section":     competitor_section,
            "general_section":        general_section,
        })
    except Exception as exc:
        logger.error("Structured LLM generation failed: %s", exc)
        raise
