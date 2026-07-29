"""
Outline Parser Service.

Converts free-form chapter outline text written by an author into the
structured {chapters: [{title, sections:[{title, description}]}]} format
that the rest of the pipeline expects.

Supported formats
-----------------
Format A (explicit "Chapter N:")
    Chapter 1: Why You Can't Focus
    * The myth of laziness
    * Digital distractions

Format B (numbered list)
    1. Why You Can't Focus
       * The myth of laziness
    2. Understanding Attention
       * Deep work

Format C (bare heading + bullets)
    Why You Can't Focus
    • The myth of laziness
    • Digital distractions

Also supports:
  - "Chapter 1 - Title" / "CHAPTER 1 Title"
  - "Part / Section / Unit / Module N: Title"
  - "1) Title" / "01. Title"
  - ALL-CAPS section headings
  - Numbered sub-items (1.1, 1.1., a., i.)
  - Indented lines (≥ 2 spaces or tab) as sections

Original text is stored alongside the parsed structure.
"""
from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Regex patterns ─────────────────────────────────────────────────────────────

# Chapter-level matchers — tried in order; first match wins.
_CHAPTER_PATTERNS: List[re.Pattern] = [
    # "Chapter 1: Title" / "Chapter 1 - Title" / "CHAPTER 1 Title"
    re.compile(
        r"^chapter\s+(\d+|[IVXivx]+)\s*[:–—\-]?\s*(.+)$",
        re.IGNORECASE,
    ),
    # "Part 1: Title" / "Section I:" / "Unit 2 — Title" / "Module 3: ..."
    re.compile(
        r"^(?:part|section|unit|module)\s+(\d+|[IVXivx]+)\s*[:–—\-]?\s*(.+)$",
        re.IGNORECASE,
    ),
    # "1. Title" / "1) Title" / "01. Title"
    re.compile(r"^(\d{1,2})[.)]\s+(.+)$"),
]

# Sub-item (section) matchers
_SECTION_PATTERNS: List[re.Pattern] = [
    # Standard bullets: "- item" / "• item" / "* item" / "· item"
    re.compile(r"^\s*[-•*·]\s+(.+)$"),
    # Numbered sub: "1.1 Title" / "1.1. Title" / "a. Title" / "i. Title"
    re.compile(r"^\s*(?:\d+\.\d+\.?\s+|[a-z][.)]\s+|[ivxlIVXL]+[.)]\s+)(.+)$"),
    # Indented line (≥ 2 spaces or tab)
    re.compile(r"^(?:\t|  +)(.+)$"),
]

# Lines that look like ALL-CAPS headings (≥ 3 uppercase words, no lowercase)
_ALLCAPS_RE = re.compile(r"^[A-Z][A-Z\s\d:'\-,&]{4,}$")


def _is_chapter_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Return (chapter_number_str, title) if line looks like a chapter heading,
    else None.
    """
    stripped = line.strip()
    if not stripped:
        return None
    for pat in _CHAPTER_PATTERNS:
        m = pat.match(stripped)
        if m:
            num, title = m.group(1), m.group(2).strip()
            if title:
                return num, title
    return None


def _is_section_line(line: str) -> Optional[str]:
    """Return the section title if the line is a sub-item, else None."""
    for pat in _SECTION_PATTERNS:
        m = pat.match(line)
        if m:
            val = m.group(1).strip()
            return val if val else None
    return None


# ── Duplicate-removal helper ───────────────────────────────────────────────────

def _dedup_chapters(chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove chapters with duplicate titles (case-insensitive), preserving
    original ordering (first occurrence wins).
    """
    seen: set = set()
    unique: List[Dict[str, Any]] = []
    for ch in chapters:
        key = ch.get("title", "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(ch)
    return unique


# ── Core parser ────────────────────────────────────────────────────────────────

def parse_outline_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse free-form outline text into a list of chapter dicts.

    Returns
    -------
    list of {title: str, sections: [{title: str, description: str|None}]}

    Strategy
    --------
    1. Line-by-line scan.
    2. Explicit chapter patterns (Format A / Format B) take priority.
    3. Bare non-indented, non-bullet lines start a new chapter when no
       chapter is open yet (Format C), or are treated as sections when a
       chapter is already open.
    4. Bullets / indented lines are always sections of the current chapter.
    5. Duplicate chapter titles are removed (first occurrence preserved).
    """
    chapters: List[Dict[str, Any]] = []
    current_chapter: Optional[Dict[str, Any]] = None

    lines = text.splitlines()
    for raw_line in lines:
        line = raw_line.rstrip()

        # Skip blank lines
        if not line.strip():
            continue

        # ── 1. Explicit chapter heading? ──────────────────────────────────
        chapter_match = _is_chapter_line(line)
        if chapter_match:
            if current_chapter is not None:
                chapters.append(current_chapter)
            _, title = chapter_match
            current_chapter = {"title": title, "sections": []}
            continue

        # ── 2. Sub-item / section bullet? ─────────────────────────────────
        section_title = _is_section_line(line)
        if section_title:
            if current_chapter is None:
                # Orphan bullet before any chapter — silently skip
                continue
            current_chapter["sections"].append({
                "title": section_title,
                "description": None,
            })
            continue

        # ── 3. Bare non-indented, non-bullet line ─────────────────────────
        stripped = line.strip()
        if stripped and len(stripped) >= 2:
            if current_chapter is None:
                # Format C: first bare line starts the first chapter
                current_chapter = {"title": stripped, "sections": []}
            else:
                # Bare line inside a chapter → treat as a new chapter heading
                # only if it looks like a title (no bullet prefix, not indented)
                # and is not a continuation of the previous section.
                # Heuristic: if it appears to be a heading (short, title-case or
                # ALL-CAPS), start a new chapter; otherwise treat as section.
                if (
                    len(stripped.split()) <= 12
                    and not stripped.endswith(",")
                    and not stripped.endswith(";")
                ):
                    chapters.append(current_chapter)
                    current_chapter = {"title": stripped, "sections": []}
                else:
                    # Long prose → treat as a section entry
                    current_chapter["sections"].append({
                        "title": stripped,
                        "description": None,
                    })

    # Flush last chapter
    if current_chapter is not None:
        chapters.append(current_chapter)

    # Deduplicate
    chapters = _dedup_chapters(chapters)

    logger.info(
        "Outline parser: %d chapter(s) parsed from free-form text.", len(chapters)
    )
    return chapters


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_outline(chapters: List[Dict[str, Any]]) -> List[str]:
    """
    Validate a parsed chapter list.

    Rules
    -----
    * At least one chapter must be present  →  hard error (list not empty).
    * Each chapter must have a non-empty title  →  error per chapter.
    * Empty sections are *allowed* (just a warning).
    * Duplicate titles were already removed by the parser (no check needed).

    Returns
    -------
    list of error/warning strings — empty list means fully valid.
    """
    errors: List[str] = []

    if not chapters:
        errors.append(
            "No chapters could be detected. Make sure each chapter starts with "
            "'Chapter N:', 'N. Title', or a plain heading followed by bullet points."
        )
        return errors   # nothing further to validate

    for i, ch in enumerate(chapters, 1):
        title = ch.get("title", "").strip()
        if not title:
            errors.append(f"Chapter {i} has an empty title.")

    # Soft warnings (non-blocking)
    for i, ch in enumerate(chapters, 1):
        if not ch.get("sections"):
            errors.append(
                f"⚠ Chapter {i} ('{ch.get('title', '?')}') has no sub-sections — "
                "consider adding bullet points for key topics."
            )

    return errors


# ── Public pipeline helper ─────────────────────────────────────────────────────

def outline_text_to_request_dict(text: str) -> Dict[str, Any]:
    """
    Full pipeline: raw text → validated parsed dict.

    Returns
    -------
    {
      "chapters":      [...],
      "original_text": "...",
      "warnings":      [...]   # empty = clean
    }
    """
    chapters = parse_outline_text(text)
    warnings = validate_outline(chapters)
    return {
        "chapters":      chapters,
        "original_text": text.strip(),
        "warnings":      warnings,
    }
