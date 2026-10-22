"""Input and output validation helpers."""

from __future__ import annotations

import re
import unicodedata
import zipfile
from pathlib import Path

from src.config import CONFIG
from src.exceptions import InvalidPDFError, OutputValidationError, OversizedDocumentError

PDF_MAGIC = b"%PDF-"
SAFE_NAME_RE = re.compile(r"[^\w.\-]+", re.UNICODE)


def sanitize_filename(name: str | None, default: str = "document") -> str:
    """Return a path-safe basename without directory components."""
    if not name:
        stem = default
    else:
        candidate = Path(str(name).replace("\\", "/")).name
        candidate = unicodedata.normalize("NFKC", candidate)
        candidate = candidate.strip()
        if not candidate:
            stem = default
        else:
            stem = Path(candidate).stem
    stem = SAFE_NAME_RE.sub("_", stem).strip("._") or default
    return stem[:80]


def output_docx_name(original_name: str | None) -> str:
    return f"{sanitize_filename(original_name)}.docx"


def ensure_allowed_size(size_bytes: int, *, max_bytes: int | None = None) -> None:
    limit = max_bytes if max_bytes is not None else CONFIG.max_upload_bytes
    if size_bytes <= 0:
        raise InvalidPDFError("The uploaded file is empty. Choose a valid PDF and try again.")
    if size_bytes > limit:
        limit_mb = max(1, limit // (1024 * 1024))
        raise OversizedDocumentError(
            f"This file is larger than the {limit_mb} MB upload limit. "
            "Split the PDF or increase DOCSHIFT_MAX_UPLOAD_MB if your computer has enough RAM and disk space."
        )


def looks_like_pdf(data: bytes) -> bool:
    if not data:
        return False
    head = data[:1024].lstrip(b"\x00 \t\r\n")
    return head.startswith(PDF_MAGIC)


def validate_pdf_bytes(data: bytes, filename: str | None = None) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix and suffix != ".pdf":
        raise InvalidPDFError("Only PDF files are supported. Please upload a file with a .pdf extension.")
    if not looks_like_pdf(data):
        raise InvalidPDFError(
            "This file does not look like a valid PDF. It may be damaged, renamed, or a different format."
        )
    ensure_allowed_size(len(data))


def validate_docx_file(path: Path) -> None:
    """Confirm the file is a real Office Open XML document, not a renamed PDF."""
    if not path.exists() or path.stat().st_size < 64:
        raise OutputValidationError("Conversion finished but the Word file was empty or incomplete. Please try again.")
    if path.suffix.lower() != ".docx":
        raise OutputValidationError("The output file is missing a .docx extension.")
    if not zipfile.is_zipfile(path):
        raise OutputValidationError(
            "The output is not a valid Word document. Conversion may have failed."
        )
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise OutputValidationError(
                    "The Word file is missing required document parts and cannot be opened reliably."
                )
            xml = archive.read("word/document.xml")
            if b"<w:document" not in xml:
                raise OutputValidationError("The Word file document body is invalid.")
    except OutputValidationError:
        raise
    except Exception as exc:
        raise OutputValidationError("The Word file could not be validated. Please try converting again.") from exc

    try:
        from docx import Document

        Document(str(path))
    except Exception as exc:
        raise OutputValidationError(
            "Microsoft Word compatible applications may not open this file. Please try converting again."
        ) from exc
