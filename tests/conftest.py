"""Shared test fixtures and synthetic PDFs."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pymupdf as fitz
import pytest
from PIL import Image


def write_text_pdf(path: Path, text: str = "Hello DocShift", pages: int = 1) -> Path:
    document = fitz.open()
    for index in range(pages):
        page = document.new_page(width=612, height=792)
        page.insert_text((72, 72), f"{text} page {index + 1}")
    document.save(path)
    document.close()
    return path


def write_image_pdf(path: Path) -> Path:
    image = Image.new("RGB", (200, 80), color=(20, 80, 180))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_image(fitz.Rect(72, 72, 272, 152), stream=buffer.getvalue())
    document.save(path)
    document.close()
    return path


def write_table_pdf(path: Path) -> Path:
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 50), "Quarterly figures")
    cells = [("Item", "Qty"), ("Pens", "12"), ("Paper", "4")]
    y = 80
    for row in cells:
        x = 72
        for value in row:
            rect = fitz.Rect(x, y, x + 120, y + 24)
            page.draw_rect(rect)
            page.insert_text((x + 8, y + 16), value)
            x += 120
        y += 24
    document.save(path)
    document.close()
    return path


@pytest.fixture()
def text_pdf(tmp_path: Path) -> Path:
    return write_text_pdf(tmp_path / "sample.pdf")


@pytest.fixture()
def image_pdf(tmp_path: Path) -> Path:
    return write_image_pdf(tmp_path / "image.pdf")


@pytest.fixture()
def table_pdf(tmp_path: Path) -> Path:
    return write_table_pdf(tmp_path / "table.pdf")


@pytest.fixture()
def encrypted_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "locked.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "secret")
    document.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    document.close()
    return path
