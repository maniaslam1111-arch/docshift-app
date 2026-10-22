"""PDF to DOCX conversion engine."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from src.exceptions import ConversionError, OutputValidationError
from src.file_manager import format_bytes
from src.ocr import ocr_pdf_to_docx
from src.pdf_inspector import PDFInspection, inspect_pdf
from src.validators import output_docx_name, validate_docx_file

logger = logging.getLogger("docshift")

ProgressCallback = Callable[[str], None]


@dataclass
class ConversionResult:
    source_name: str
    output_name: str
    source_size: int
    output_size: int
    page_count: int
    used_ocr: bool
    warnings: list[str] = field(default_factory=list)
    images_extracted: int = 0

    @property
    def source_size_label(self) -> str:
        return format_bytes(self.source_size)

    @property
    def output_size_label(self) -> str:
        return format_bytes(self.output_size)


def _notify(callback: ProgressCallback | None, message: str) -> None:
    if callback:
        callback(message)


def _convert_with_pdf2docx(pdf_path: Path, docx_path: Path) -> None:
    try:
        from pdf2docx import Converter
    except ImportError as exc:
        raise ConversionError(
            "The conversion library is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    converter = None
    try:
        converter = Converter(str(pdf_path))
        converter.convert(str(docx_path))
    except MemoryError as exc:
        raise ConversionError(
            "The computer ran out of memory while converting this PDF. Try a smaller file or fewer pages."
        ) from exc
    except OSError as exc:
        if getattr(exc, "errno", None) == 28:
            raise ConversionError("There is not enough disk space to finish conversion.") from exc
        raise ConversionError("Conversion failed because of a file or disk error. Try again.") from exc
    except Exception as exc:
        raise ConversionError(
            "Conversion failed. Complex or damaged PDFs sometimes cannot be turned into Word automatically."
        ) from exc
    finally:
        if converter is not None:
            try:
                converter.close()
            except Exception:
                logger.debug("Converter close failed.")


def convert_pdf_to_docx(
    pdf_path: Path,
    docx_path: Path,
    *,
    original_name: str,
    use_ocr: bool = False,
    inspection: PDFInspection | None = None,
    progress: ProgressCallback | None = None,
) -> ConversionResult:
    _notify(progress, "Inspecting PDF…")
    info = inspection or inspect_pdf(pdf_path)
    warnings = list(info.warnings)

    if use_ocr:
        _notify(progress, "Running local OCR…")
        ocr_pdf_to_docx(pdf_path, docx_path)
        warnings.append(
            "OCR was used. Spelling, punctuation, and layout may be wrong. Review the Word file before you rely on it."
        )
        used_ocr = True
    else:
        _notify(progress, "Converting layout, text, tables, and images…")
        _convert_with_pdf2docx(pdf_path, docx_path)
        used_ocr = False
        if info.likely_scanned:
            warnings.append(
                "This looked like a scanned PDF and OCR was not used, so the Word file may contain little editable text."
            )

    _notify(progress, "Validating the Word document…")
    try:
        validate_docx_file(docx_path)
    except OutputValidationError:
        raise

    output_size = docx_path.stat().st_size
    if output_size < 200 and info.page_count > 1:
        warnings.append("The Word file is unusually small. Some pages may not have converted cleanly.")

    warnings.append(
        "Layout fidelity is best-effort. Complex columns, forms, annotations, and vector drawings may need manual correction."
    )

    _notify(progress, "Conversion complete.")
    return ConversionResult(
        source_name=Path(original_name).name,
        output_name=output_docx_name(original_name),
        source_size=info.file_size,
        output_size=output_size,
        page_count=info.page_count,
        used_ocr=used_ocr,
        warnings=warnings,
    )
