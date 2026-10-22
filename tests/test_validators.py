from pathlib import Path

import pytest
from docx import Document

from src.exceptions import InvalidPDFError, OutputValidationError, OversizedDocumentError
from src.validators import (
    looks_like_pdf,
    output_docx_name,
    sanitize_filename,
    validate_docx_file,
    validate_pdf_bytes,
)


def test_sanitize_filename_strips_paths_and_unsafe_chars() -> None:
    assert sanitize_filename(r"..\..\secret\invoice*.pdf") == "invoice"
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd"
    assert "\\" not in sanitize_filename("C:\\Windows\\file.pdf")
    assert "/" not in sanitize_filename("My Invoice (2024).pdf")
    assert sanitize_filename(None) == "document"
    assert output_docx_name("report.pdf") == "report.docx"


def test_looks_like_pdf_accepts_header_and_rejects_garbage() -> None:
    assert looks_like_pdf(b"%PDF-1.7\n%")
    assert not looks_like_pdf(b"PK\x03\x04not-a-pdf")
    assert not looks_like_pdf(b"")


def test_validate_pdf_bytes_rejects_wrong_type_and_empty() -> None:
    with pytest.raises(InvalidPDFError):
        validate_pdf_bytes(b"not a pdf", "file.pdf")
    with pytest.raises(InvalidPDFError):
        validate_pdf_bytes(b"%PDF-1.4", "notes.txt")
    with pytest.raises(InvalidPDFError):
        validate_pdf_bytes(b"", "file.pdf")


def test_validate_pdf_bytes_rejects_oversized() -> None:
    from src.validators import ensure_allowed_size

    with pytest.raises(OversizedDocumentError):
        ensure_allowed_size(2 * 1024 * 1024, max_bytes=1024)


def test_validate_docx_file_accepts_real_docx(tmp_path: Path) -> None:
    path = tmp_path / "ok.docx"
    Document().save(path)
    validate_docx_file(path)


def test_validate_docx_file_rejects_renamed_pdf_and_corrupt(tmp_path: Path) -> None:
    fake = tmp_path / "fake.docx"
    fake.write_bytes(b"%PDF-1.7 renamed")
    with pytest.raises(OutputValidationError):
        validate_docx_file(fake)

    empty = tmp_path / "empty.docx"
    empty.write_bytes(b"PK")
    with pytest.raises(OutputValidationError):
        validate_docx_file(empty)
