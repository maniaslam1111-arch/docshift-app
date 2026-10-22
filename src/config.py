"""Configurable application limits and environment settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        return


_load_dotenv()


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class AppConfig:
    max_upload_mb: int = 50
    max_pages: int = 200
    ocr_dpi: int = 200
    min_chars_per_page: int = 20
    session_ttl_seconds: int = 3600

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            max_upload_mb=_int_env("DOCSHIFT_MAX_UPLOAD_MB", 50),
            max_pages=_int_env("DOCSHIFT_MAX_PAGES", 200),
            ocr_dpi=_int_env("DOCSHIFT_OCR_DPI", 200),
            min_chars_per_page=_int_env("DOCSHIFT_MIN_CHARS_PER_PAGE", 20),
            session_ttl_seconds=_int_env("DOCSHIFT_SESSION_TTL_SECONDS", 3600),
        )


CONFIG = AppConfig.from_env()
