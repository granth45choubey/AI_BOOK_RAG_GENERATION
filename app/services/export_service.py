"""
Export Engine — converts structured book JSON into downloadable documents.

Supports editable DOCX and PDF (via DOCX conversion). Independent from the
Book Writing Engine; only formats existing structured data.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.schemas.export import BookChapter, BookSection, StructuredBook
from app.utils.config import get_settings
from app.utils.document_formatter import build_manuscript_docx, parse_content_into_sections
from app.utils.pdf_formatter import build_manuscript_pdf

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Raised when export cannot complete."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class PdfConversionError(ExportError):
    """Raised when DOCX → PDF conversion fails or is unavailable."""


# ── PDF backend abstraction ───────────────────────────────────────────────────


class PdfConverterBackend(ABC):
    """Pluggable PDF conversion backend (docx2pdf, LibreOffice, ReportLab, …)."""

    name: str = "unknown"

    @abstractmethod
    def convert(self, docx_path: Path, pdf_path: Path) -> None:
        """Convert DOCX at docx_path to PDF at pdf_path."""


def _validate_pdf_output(pdf_path: Path) -> None:
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise PdfConversionError(
            "PDF conversion completed but no output file was produced.",
            detail=f"Expected file: {pdf_path}",
        )


class Docx2PdfBackend(PdfConverterBackend):
    """PDF conversion using docx2pdf (requires Microsoft Word on Windows/macOS)."""

    name = "docx2pdf"

    def convert(self, docx_path: Path, pdf_path: Path) -> None:
        from docx2pdf import convert as docx2pdf_convert

        docx2pdf_convert(str(docx_path.resolve()), str(pdf_path.resolve()))
        _validate_pdf_output(pdf_path)


class Win32WordBackend(PdfConverterBackend):
    """
    PDF conversion via Microsoft Word COM automation (Windows only).

    Fallback when docx2pdf is not installed but pywin32 + Word are available.
    """

    name = "win32com"

    # wdFormatPDF — https://learn.microsoft.com/en-us/office/vba/api/word.wdsaveformat
    _WD_FORMAT_PDF = 17

    def convert(self, docx_path: Path, pdf_path: Path) -> None:
        import win32com.client  # type: ignore[import-untyped]

        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = None
        try:
            doc = word.Documents.Open(str(docx_path.resolve()))
            doc.SaveAs(str(pdf_path.resolve()), FileFormat=self._WD_FORMAT_PDF)
        finally:
            if doc is not None:
                doc.Close(False)
            word.Quit()

        _validate_pdf_output(pdf_path)


class ReportLabBackend(PdfConverterBackend):
    """Direct PDF generation via ReportLab — no Word or pywin32 required."""

    name = "reportlab"

    def __init__(self, book: StructuredBook):
        self._book = book

    def convert(self, docx_path: Path, pdf_path: Path) -> None:
        build_manuscript_pdf(self._book, pdf_path)
        _validate_pdf_output(pdf_path)


class ChainedPdfConverter(PdfConverterBackend):
    """Try multiple PDF backends in order until one succeeds."""

    name = "chained"

    def __init__(self, backends: List[PdfConverterBackend]):
        self._backends = backends

    def convert(self, docx_path: Path, pdf_path: Path) -> None:
        errors: List[str] = []

        for backend in self._backends:
            try:
                backend.convert(docx_path, pdf_path)
                logger.info("PDF converted using %s backend", backend.name)
                return
            except ImportError as exc:
                errors.append(f"{backend.name}: missing dependency ({exc})")
            except PdfConversionError as exc:
                errors.append(f"{backend.name}: {exc.message}")
            except Exception as exc:
                errors.append(f"{backend.name}: {exc}")

        raise PdfConversionError(
            "PDF conversion failed with all available backends.",
            detail=f"Attempts: {'; '.join(errors)}",
        )


def _word_pdf_available() -> bool:
    """True when Word-based DOCX→PDF conversion can run on this machine."""
    if sys.platform == "win32":
        try:
            import pywintypes  # noqa: F401
            import docx2pdf  # noqa: F401
            return True
        except ImportError:
            return False
    if sys.platform == "darwin":
        try:
            import docx2pdf  # noqa: F401
            return True
        except ImportError:
            return False
    return False


def _build_pdf_backends(book: StructuredBook) -> List[PdfConverterBackend]:
    """ReportLab always available; Word backends only when dependencies resolve."""
    backends: List[PdfConverterBackend] = []

    if _word_pdf_available():
        if sys.platform == "win32":
            backends.append(Docx2PdfBackend())
            backends.append(Win32WordBackend())
        elif sys.platform == "darwin":
            backends.append(Docx2PdfBackend())
    else:
        logger.info(
            "Word PDF conversion unavailable — using ReportLab direct PDF export."
        )

    backends.append(ReportLabBackend(book))
    return backends


def get_pdf_converter(book: StructuredBook) -> PdfConverterBackend:
    """Return the active PDF converter. Swap implementation here for other backends."""
    return ChainedPdfConverter(_build_pdf_backends(book))


# ── Path helpers ──────────────────────────────────────────────────────────────


def _exports_dir() -> Path:
    path = Path(get_settings().exports_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _generated_book_path() -> Path:
    return Path(get_settings().generated_book_store_path)


def _safe_filename(title: str, extension: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "_", slug.strip())
    slug = slug[:80] or "book"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{timestamp}.{extension}"


def build_download_url(filename: str) -> str:
    return f"/export/download/{filename}"


# ── Book persistence ──────────────────────────────────────────────────────────


def save_generated_book(book: StructuredBook) -> Path:
    """Persist structured book JSON for later export."""
    path = _generated_book_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = book.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved generated book to %s (%d chapters)", path, len(book.chapters))
    return path


def load_generated_book() -> Optional[StructuredBook]:
    """Load the last saved structured book, or None if missing."""
    path = _generated_book_path()
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return StructuredBook.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ExportError(
            "Stored book JSON is invalid. Re-save the generated book before exporting.",
            detail=str(exc),
        ) from exc


def resolve_book(book_override: Optional[StructuredBook] = None) -> StructuredBook:
    """Resolve book from inline override or persisted storage."""
    if book_override is not None:
        save_generated_book(book_override)
        return book_override

    stored = load_generated_book()
    if stored is None:
        raise ExportError(
            "No generated book found. Generate chapters first or POST the structured book.",
        )
    return stored


def normalise_chapter_content(chapter: BookChapter) -> BookChapter:
    """
    Ensure chapters with flat content are split into intro + sections when possible.
    Does not regenerate prose — only restructures existing text.
    """
    if chapter.sections:
        return chapter

    intro, parsed_sections = parse_content_into_sections(chapter.content)
    if not parsed_sections:
        return chapter

    sections = [
        BookSection(heading=heading, content=body)
        for heading, body in parsed_sections
        if heading.strip()
    ]
    return BookChapter(title=chapter.title, content=intro, sections=sections)


def normalise_book(book: StructuredBook) -> StructuredBook:
    chapters = [normalise_chapter_content(ch) for ch in book.chapters]
    return book.model_copy(update={"chapters": chapters})


# ── Export operations ─────────────────────────────────────────────────────────


def export_docx(book: StructuredBook) -> tuple[Path, str]:
    """
    Export structured book to an editable DOCX file.

    Returns (absolute_path, download_url).
    """
    try:
        normalised = normalise_book(book)
        document = build_manuscript_docx(normalised)
        filename = _safe_filename(book.title, "docx")
        output_path = _exports_dir() / filename
        document.save(str(output_path))
        logger.info("DOCX export written: %s", output_path)
        return output_path, build_download_url(filename)
    except ExportError:
        raise
    except OSError as exc:
        raise ExportError("Failed to write DOCX file.", detail=str(exc)) from exc
    except Exception as exc:
        raise ExportError("DOCX export failed.", detail=str(exc)) from exc


def export_pdf(book: StructuredBook) -> tuple[Path, str]:
    """
    Export structured book to PDF.

    Tries Word-based DOCX→PDF when available, otherwise generates PDF directly
    via ReportLab (no Microsoft Word or pywin32 required).

    Returns (absolute_path, download_url).
    """
    try:
        normalised = normalise_book(book)
        pdf_filename = _safe_filename(book.title, "pdf")
        pdf_path = _exports_dir() / pdf_filename

        # Build DOCX as intermediate for Word-based converters (optional path).
        docx_filename = pdf_filename.replace(".pdf", ".docx")
        docx_path = _exports_dir() / docx_filename
        document = build_manuscript_docx(normalised)
        document.save(str(docx_path))

        converter = get_pdf_converter(normalised)
        converter.convert(docx_path, pdf_path)

        logger.info("PDF export written: %s", pdf_path)
        return pdf_path, build_download_url(pdf_filename)
    except PdfConversionError:
        raise
    except ExportError:
        raise
    except OSError as exc:
        raise ExportError("Failed to write PDF file.", detail=str(exc)) from exc
    except Exception as exc:
        raise ExportError("PDF export failed.", detail=str(exc)) from exc


def get_export_file(filename: str) -> Path:
    """Resolve an export file for download; raises ExportError if not found."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ExportError("Invalid filename.")

    path = _exports_dir() / filename
    if not path.exists() or not path.is_file():
        raise ExportError("Export file not found.", detail=filename)
    return path
