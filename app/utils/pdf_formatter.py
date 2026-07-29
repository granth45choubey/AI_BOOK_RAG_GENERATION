"""
Direct PDF manuscript builder using ReportLab.

Generates professional PDFs without Microsoft Word or pywin32.
Used as the primary/fallback PDF backend when DOCX→PDF conversion is unavailable.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import List

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.schemas.export import BookChapter, StructuredBook

_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
_BULLET_RE = re.compile(r"^[-*•]\s+(.+)$")
_NUMBERED_RE = re.compile(r"^\d+[.)]\s+(.+)$")
_INLINE_PATTERN = re.compile(
    r"(\*\*.+?\*\*|__.+?__|\*(?!\*).+?(?<!\*)\*(?!\*)|_.+?_)"
)


def _escape_xml(text: str) -> str:
    return html.escape(text, quote=False)


def _markdown_to_reportlab(text: str) -> str:
    """Convert lightweight markdown inline markers to ReportLab XML tags."""
    if not text:
        return ""

    pos = 0
    parts: List[str] = []

    for match in _INLINE_PATTERN.finditer(text):
        if match.start() > pos:
            parts.append(_escape_xml(text[pos : match.start()]))

        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            parts.append(f"<b>{_escape_xml(token[2:-2])}</b>")
        elif token.startswith("__") and token.endswith("__"):
            parts.append(f"<b>{_escape_xml(token[2:-2])}</b>")
        elif token.startswith("*") and token.endswith("*"):
            parts.append(f"<i>{_escape_xml(token[1:-1])}</i>")
        elif token.startswith("_") and token.endswith("_"):
            parts.append(f"<i>{_escape_xml(token[1:-1])}</i>")
        pos = match.end()

    if pos < len(text):
        parts.append(_escape_xml(text[pos:]))

    return "".join(parts)


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "BookTitle",
            parent=base["Title"],
            fontName="Times-Roman",
            fontSize=28,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "subtitle": ParagraphStyle(
            "BookSubtitle",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=24,
        ),
        "author": ParagraphStyle(
            "BookAuthor",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "toc_title": ParagraphStyle(
            "TocTitle",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=24,
        ),
        "toc_entry": ParagraphStyle(
            "TocEntry",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=12,
            leading=18,
            leftIndent=18,
            spaceAfter=8,
        ),
        "chapter_label": ParagraphStyle(
            "ChapterLabel",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=18,
            leading=22,
            spaceAfter=6,
        ),
        "chapter_title": ParagraphStyle(
            "ChapterTitle",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=18,
            leading=22,
            spaceAfter=14,
        ),
        "section_title": ParagraphStyle(
            "SectionTitle",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=12,
            leading=18,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=12,
            leading=18,
            leftIndent=36,
            rightIndent=18,
            textColor="#444444",
            spaceAfter=10,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=12,
            leading=18,
            leftIndent=24,
            bulletIndent=12,
            spaceAfter=4,
        ),
    }


def _render_content(story: list, content: str, styles: dict[str, ParagraphStyle]) -> None:
    if not content or not content.strip():
        return

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        quote_match = _BLOCKQUOTE_RE.match(stripped)
        if quote_match:
            story.append(
                Paragraph(_markdown_to_reportlab(quote_match.group(1)), styles["quote"])
            )
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            story.append(
                Paragraph(
                    _markdown_to_reportlab(heading_match.group(1)),
                    styles["section_title"],
                )
            )
            continue

        bullet_match = _BULLET_RE.match(stripped)
        if bullet_match:
            story.append(
                Paragraph(
                    f"• {_markdown_to_reportlab(bullet_match.group(1))}",
                    styles["bullet"],
                )
            )
            continue

        numbered_match = _NUMBERED_RE.match(stripped)
        if numbered_match:
            story.append(
                Paragraph(
                    f"{numbered_match.group(0).split()[0]} {_markdown_to_reportlab(numbered_match.group(1))}",
                    styles["bullet"],
                )
            )
            continue

        story.append(Paragraph(_markdown_to_reportlab(stripped), styles["body"]))


def _add_chapter(
    story: list,
    chapter_number: int,
    chapter: BookChapter,
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(Paragraph(f"Chapter {chapter_number}", styles["chapter_label"]))
    story.append(Paragraph(_escape_xml(chapter.title), styles["chapter_title"]))

    if chapter.content and chapter.content.strip():
        _render_content(story, chapter.content, styles)

    for section in chapter.sections:
        if section.heading.strip():
            story.append(
                Paragraph(_escape_xml(section.heading.strip()), styles["section_title"])
            )
        if section.content.strip():
            _render_content(story, section.content, styles)


def build_manuscript_pdf(book: StructuredBook, output_path: Path) -> Path:
    """Write a formatted PDF manuscript directly from structured book data."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _build_styles()
    story: list = []

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title=book.title,
        author=book.author or "",
    )

    story.append(Spacer(1, 2.5 * inch))
    story.append(Paragraph(_escape_xml(book.title), styles["title"]))
    if book.subtitle:
        story.append(Paragraph(_escape_xml(book.subtitle), styles["subtitle"]))
    if book.author:
        story.append(Spacer(1, 0.4 * inch))
        story.append(Paragraph(_escape_xml(book.author), styles["author"]))
    story.append(PageBreak())

    story.append(Paragraph("Table of Contents", styles["toc_title"]))
    for index, chapter in enumerate(book.chapters, start=1):
        story.append(
            Paragraph(
                f"Chapter {index}: {_escape_xml(chapter.title)}",
                styles["toc_entry"],
            )
        )
    story.append(PageBreak())

    for index, chapter in enumerate(book.chapters, start=1):
        if index > 1:
            story.append(PageBreak())
        _add_chapter(story, index, chapter, styles)

    doc.build(story)
    return output_path
