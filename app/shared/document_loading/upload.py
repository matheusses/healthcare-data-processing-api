"""Public API for validating and extracting text from uploaded files."""

import os

from fastapi import UploadFile

from app.config import settings
from app.shared.document_loading.extractor import DocumentExtractor
from app.shared.exceptions import DomainException

ALLOWED_EXTENSIONS = frozenset({".txt", ".pdf", ".jpg", ".jpeg", ".png"})

_EXTENSION_TO_CONTENT_TYPE = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _normalize_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.split(";")[0].strip().lower()


def validate_upload_file_type(filename: str | None, content_type: str | None = None) -> None:
    """
    Validate that the upload has an allowed extension and optionally content type.

    Raises DomainException with code INVALID_FILE_TYPE if validation fails.
    """
    if filename is None or (isinstance(filename, str) and not filename.strip()):
        raise DomainException("Filename is required.", code="INVALID_FILE_TYPE")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DomainException(
            f"File extension '{ext}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
            code="INVALID_FILE_TYPE",
        )

    if content_type is not None:
        normalized = _normalize_content_type(content_type)
        allowed = [x.strip().lower() for x in settings.ALLOWED_CONTENT_TYPES.split(",")]
        if normalized not in allowed:
            raise DomainException(
                f"Content type '{content_type}' is not allowed.",
                code="INVALID_FILE_TYPE",
            )


def _content_type_from_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    ct = _EXTENSION_TO_CONTENT_TYPE.get(ext)
    if not ct:
        raise DomainException(f"Unsupported extension: {ext}.", code="INVALID_FILE_TYPE")
    return ct


async def extract_text_from_upload(upload_file: UploadFile) -> str:
    """
    Validate the upload, read the file, and extract plain text.

    - .txt: decode as UTF-8.
    - .pdf: PyPDFLoader (LangChain).
    - .jpg / .jpeg / .png: OCR (RapidOCR).

    Raises DomainException (INVALID_FILE_TYPE or EXTRACTION_ERROR) on failure.
    """
    validate_upload_file_type(upload_file.filename, upload_file.content_type)

    raw = await upload_file.read()
    if not raw:
        raise DomainException("File is empty.", code="INVALID_FILE_TYPE")

    content_type = _normalize_content_type(upload_file.content_type) or (
        _content_type_from_filename(upload_file.filename or "")
    )

    extractor = DocumentExtractor()
    return await extractor.extract_text_from_upload(raw, content_type)
