"""Temporary file handling with unique names and best-effort cleanup."""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from src.validators import sanitize_filename

logger = logging.getLogger("docshift")


class TempWorkspace:
    """A unique temporary folder for one conversion session."""

    def __init__(self) -> None:
        self.id = uuid.uuid4().hex
        self.root = Path(tempfile.mkdtemp(prefix=f"docshift_{self.id}_"))
        self.closed = False

    def save_upload(self, data: bytes, original_name: str | None) -> Path:
        safe = sanitize_filename(original_name)
        path = self.root / f"source_{self.id}_{safe}.pdf"
        path.write_bytes(data)
        return path

    def output_path(self, original_name: str | None) -> Path:
        from src.validators import output_docx_name

        return self.root / f"output_{self.id}_{output_docx_name(original_name)}"

    def images_zip_path(self) -> Path:
        return self.root / f"images_{self.id}.zip"

    def cleanup(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            shutil.rmtree(self.root, ignore_errors=False)
        except OSError:
            logger.warning("Temporary files could not be removed completely.")
            shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self) -> "TempWorkspace":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.2f} MB"
