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
