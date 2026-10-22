"""User-facing application errors."""

from __future__ import annotations


class DocShiftError(Exception):
    """An error that can be shown to the user without internal paths."""

    def __init__(self, user_message: str, *, log_message: str | None = None) -> None:
        super().__init__(log_message or user_message)
        self.user_message = user_message
        self.log_message = log_message or user_message


class InvalidPDFError(DocShiftError):
    pass


class EncryptedPDFError(DocShiftError):
    pass


class OversizedDocumentError(DocShiftError):
    pass


class ConversionError(DocShiftError):
    pass


class OCRUnavailableError(DocShiftError):
    pass


class OutputValidationError(DocShiftError):
    pass
