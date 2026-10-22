from pathlib import Path

import pytest

from src.exceptions import EncryptedPDFError, InvalidPDFError
from src.file_manager import TempWorkspace
from src.pdf_inspector import extract_embedded_images, inspect_pdf


def test_inspect_counts_pages_and_text(text_pdf: Path) -> None:
    info = inspect_pdf(text_pdf)
    assert info.page_count == 1
    assert info.extractable_chars > 0
    assert info.likely_scanned is False
    assert info.is_encrypted is False


def test_inspect_marks_image_only_as_likely_scanned(image_pdf: Path) -> None:
    info = inspect_pdf(image_pdf)
    assert info.page_count == 1
    assert info.image_count >= 1
    assert info.likely_scanned is True


def test_inspect_rejects_encrypted(encrypted_pdf: Path) -> None:
    with pytest.raises(EncryptedPDFError):
        inspect_pdf(encrypted_pdf)


def test_inspect_rejects_corrupt_and_empty(tmp_path: Path) -> None:
    corrupt = tmp_path / "bad.pdf"
    corrupt.write_bytes(b"%PDF-1.7\nbroken")
    with pytest.raises(InvalidPDFError):
        inspect_pdf(corrupt)


def test_extract_images_writes_zip(image_pdf: Path, tmp_path: Path) -> None:
    zip_path = tmp_path / "images.zip"
    count = extract_embedded_images(image_pdf, zip_path)
    assert count >= 1
    assert zip_path.exists()
    assert zip_path.stat().st_size > 0


def test_temp_workspace_cleanup(tmp_path: Path, text_pdf: Path) -> None:
    workspace = TempWorkspace()
    saved = workspace.save_upload(text_pdf.read_bytes(), "demo.pdf")
    assert saved.exists()
    workspace.cleanup()
    assert not workspace.root.exists()
