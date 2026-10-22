"""PDF inspection: metadata, encryption, text density, and images."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz

from src.config import CONFIG
from src.exceptions import EncryptedPDFError, InvalidPDFError, OversizedDocumentError

logger = logging.getLogger("docshift")


@dataclass
class PDFInspection:
    page_count: int
    file_size: int
    is_encrypted: bool
    extractable_chars: int
    image_count: int
    has_tables_hint: bool
    likely_scanned: bool
    page_width_pt: float | None
    page_height_pt: float | None
    is_landscape: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def chars_per_page(self) -> float:
        if self.page_count <= 0:
            return 0.0
        return self.extractable_chars / self.page_count


def _open_pdf(path: Path) -> fitz.Document:
    try:
        document = fitz.open(path)
    except fitz.FileDataError as exc:
        raise InvalidPDFError("This PDF could not be opened. The file may be corrupted.") from exc
    except Exception as exc:
        raise InvalidPDFError("This PDF could not be read. Try exporting it again from the original application.") from exc

    if document.is_encrypted:
        document.close()
        raise EncryptedPDFError(
            "This PDF is password-protected. Remove the password in another PDF tool, then upload the unlocked file."
        )
    if document.page_count <= 0:
        document.close()
        raise InvalidPDFError("This PDF has no pages.")
    if document.page_count > CONFIG.max_pages:
        pages = document.page_count
        document.close()
        raise OversizedDocumentError(
            f"This PDF has {pages} pages, which exceeds the configured limit of {CONFIG.max_pages}. "
            "Split the document or raise DOCSHIFT_MAX_PAGES if your machine has enough memory."
        )
    return document


def inspect_pdf(path: Path) -> PDFInspection:
    document = _open_pdf(path)
    warnings: list[str] = []
    extractable_chars = 0
    image_count = 0
    table_hint = False
    width = height = None

    try:
        for index in range(document.page_count):
            page = document.load_page(index)
            if width is None:
                rect = page.rect
                width, height = rect.width, rect.height
            text = page.get_text("text") or ""
            extractable_chars += len(text.strip())
            try:
                image_count += len(page.get_images(full=True))
            except Exception:
                logger.debug("Image enumeration failed on a page; continuing.")
            try:
                if page.find_tables().tables:
                    table_hint = True
            except Exception:
                pass

        likely_scanned = (
            document.page_count > 0
            and (extractable_chars / document.page_count) < CONFIG.min_chars_per_page
        )
        if likely_scanned:
            warnings.append(
                "Very little extractable text was found. This file may be a scanned or image-based PDF. "
                "Enable OCR if Tesseract is installed, or expect limited editable text."
            )
        if image_count:
            warnings.append(
                "Images and diagrams are preserved visually when the converter can extract them. "
                "They are not converted into individually editable Word shapes."
            )
        if table_hint:
            warnings.append(
                "Tables are converted to editable Word tables when the layout is regular. "
                "Merged or nested cells may need manual cleanup."
            )

        landscape = bool(width and height and width > height)
        return PDFInspection(
            page_count=document.page_count,
            file_size=path.stat().st_size,
            is_encrypted=False,
            extractable_chars=extractable_chars,
            image_count=image_count,
            has_tables_hint=table_hint,
            likely_scanned=likely_scanned,
            page_width_pt=width,
            page_height_pt=height,
            is_landscape=landscape,
            warnings=warnings,
        )
    finally:
        document.close()


def extract_embedded_images(pdf_path: Path, zip_path: Path) -> int:
    """Write extracted images to a zip archive. Returns the number of images saved."""
    import io
    import zipfile

    from PIL import Image

    saved = 0
    seen: set[int] = set()
    document = _open_pdf(pdf_path)
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                for img in page.get_images(full=True):
                    xref = int(img[0])
                    if xref in seen:
                        continue
                    seen.add(xref)
                    try:
                        extracted = document.extract_image(xref)
                    except Exception:
                        continue
                    image_bytes = extracted.get("image")
                    ext = (extracted.get("ext") or "png").lower()
                    if not image_bytes:
                        continue
                    if ext in {"png", "jpg", "jpeg", "gif", "tif", "tiff", "bmp", "webp"}:
                        payload = image_bytes
                        suffix = "jpg" if ext == "jpeg" else ext
                    else:
                        try:
                            image = Image.open(io.BytesIO(image_bytes))
                            buffer = io.BytesIO()
                            image.convert("RGB").save(buffer, format="PNG")
                            payload = buffer.getvalue()
                            suffix = "png"
                        except Exception:
                            continue
                    saved += 1
                    archive.writestr(f"page-{page_index + 1:03d}-image-{saved:03d}.{suffix}", payload)
    finally:
        document.close()
    return saved
