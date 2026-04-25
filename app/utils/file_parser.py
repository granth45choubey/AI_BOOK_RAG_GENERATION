"""
File parsing utilities.
Supports PDF (via PyMuPDF), DOCX (via python-docx), and plain text.

Returns a list of dicts:
    {"text": str, "source": str, "page": int}
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def parse_file(file_path: str) -> List[Dict[str, Any]]:
    """Dispatch to the right parser based on file extension."""
    ext = Path(file_path).suffix.lower()
    parsers = {
        ".pdf": _parse_pdf,
        ".docx": _parse_docx,
        ".txt": _parse_txt,
    }
    parser = parsers.get(ext)
    if parser is None:
        raise ValueError(f"Unsupported file type: {ext}")
    return parser(file_path)


# ── PDF ───────────────────────────────────────────────────────────────────────

def _parse_pdf(file_path: str) -> List[Dict[str, Any]]:
    """Extract text page-by-page using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("Install PyMuPDF: pip install pymupdf")

    pages: List[Dict[str, Any]] = []
    source = os.path.basename(file_path)

    with fitz.open(file_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({
                    "text": text,
                    "source": source,
                    "page": page_num,
                })

    logger.info("Parsed PDF '%s' → %d pages", source, len(pages))
    return pages


# ── DOCX ──────────────────────────────────────────────────────────────────────

def _parse_docx(file_path: str) -> List[Dict[str, Any]]:
    """Extract text paragraph-by-paragraph from DOCX."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("Install python-docx: pip install python-docx")

    source = os.path.basename(file_path)
    doc = Document(file_path)

    full_text = "\n".join(
        para.text for para in doc.paragraphs if para.text.strip()
    )

    # Treat the whole DOCX as "page 1" (DOCX doesn't have true page numbers)
    pages = [{"text": full_text, "source": source, "page": 1}]
    logger.info("Parsed DOCX '%s' → %d characters", source, len(full_text))
    return pages


# ── TXT ───────────────────────────────────────────────────────────────────────

def _parse_txt(file_path: str) -> List[Dict[str, Any]]:
    """Read a plain text file as a single page."""
    source = os.path.basename(file_path)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read().strip()

    pages = [{"text": text, "source": source, "page": 1}]
    logger.info("Parsed TXT '%s' → %d characters", source, len(text))
    return pages
