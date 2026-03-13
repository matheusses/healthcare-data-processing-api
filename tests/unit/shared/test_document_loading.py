"""Unit tests for document_loading: validation and text extraction."""

from io import BytesIO

import pytest
from fastapi import UploadFile

from app.shared.document_loading import (
    ALLOWED_EXTENSIONS,
    extract_text_from_upload,
    validate_upload_file_type,
)
from app.shared.exceptions import DomainException


class TestValidateUploadFileType:
    """Tests for validate_upload_file_type."""

    def test_allowed_extensions_accepted(self):
        """Allowed extensions and content types pass."""
        validate_upload_file_type("note.txt", "text/plain")
        validate_upload_file_type("note.pdf", "application/pdf")
        validate_upload_file_type("note.jpg", "image/jpeg")
        validate_upload_file_type("note.jpeg", "image/jpeg")
        validate_upload_file_type("note.png", "image/png")
        validate_upload_file_type("note.PNG", None)  # content_type optional

    def test_disallowed_extension_raises(self):
        """Disallowed extensions raise DomainException with INVALID_FILE_TYPE."""
        with pytest.raises(DomainException) as exc_info:
            validate_upload_file_type("note.docx", None)
        assert exc_info.value.code == "INVALID_FILE_TYPE"
        assert "not allowed" in exc_info.value.message.lower()

        for ext in (".xml", ".html", ".doc", ".exe"):
            with pytest.raises(DomainException) as exc_info:
                validate_upload_file_type(f"x{ext}", None)
            assert exc_info.value.code == "INVALID_FILE_TYPE"

    def test_empty_or_missing_filename_raises(self):
        """Missing or empty filename raises."""
        with pytest.raises(DomainException) as exc_info:
            validate_upload_file_type(None, None)
        assert exc_info.value.code == "INVALID_FILE_TYPE"

        with pytest.raises(DomainException):
            validate_upload_file_type("", None)
        with pytest.raises(DomainException):
            validate_upload_file_type("   ", None)

    def test_content_type_checked_when_provided(self):
        """When content_type is provided, it must be in allowlist."""
        with pytest.raises(DomainException) as exc_info:
            validate_upload_file_type("note.txt", "application/octet-stream")
        assert exc_info.value.code == "INVALID_FILE_TYPE"

    def test_content_type_with_charset_ignored_suffix(self):
        """Content type with ; charset=... is normalized."""
        validate_upload_file_type("note.txt", "text/plain; charset=utf-8")


class TestExtractTextFromUpload:
    """Tests for extract_text_from_upload."""

    @pytest.mark.asyncio
    async def test_txt_returns_decoded_content(self):
        """Plain text file returns UTF-8 decoded content."""
        content = "SOAP note: Subjective and Objective data."
        f = UploadFile(filename="note.txt", file=BytesIO(content.encode("utf-8")))
        result = await extract_text_from_upload(f)
        assert result == content

    @pytest.mark.asyncio
    async def test_txt_handles_replace_errors(self):
        """Invalid UTF-8 is replaced."""
        f = UploadFile(filename="note.txt", file=BytesIO(b"ok \xff byte"))
        result = await extract_text_from_upload(f)
        assert "ok" in result

    @pytest.mark.asyncio
    async def test_empty_file_raises(self):
        """Empty file raises DomainException."""
        f = UploadFile(filename="note.txt", file=BytesIO(b""))
        with pytest.raises(DomainException) as exc_info:
            await extract_text_from_upload(f)
        assert exc_info.value.code in ("INVALID_FILE_TYPE", "EXTRACTION_ERROR")

    @pytest.mark.asyncio
    async def test_invalid_extension_raises(self):
        """Wrong extension raises before reading."""
        f = UploadFile(filename="note.docx", file=BytesIO(b"data"))
        with pytest.raises(DomainException) as exc_info:
            await extract_text_from_upload(f)
        assert exc_info.value.code == "INVALID_FILE_TYPE"

    @pytest.mark.asyncio
    async def test_pdf_extracts_text(self):
        """PDF returns extracted text string (integration with PyPDFLoader)."""
        # Minimal valid PDF structure
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
            b"4 0 obj<</Length 44>>stream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello) Tj\nET\nendstream\n"
            b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
            b"0000000115 00000 n \n0000000214 00000 n \ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n303\n%%EOF"
        )
        f = UploadFile(filename="note.pdf", file=BytesIO(pdf_bytes))
        try:
            result = await extract_text_from_upload(f)
            assert isinstance(result, str)
        except DomainException as e:
            assert e.code == "EXTRACTION_ERROR"

    @pytest.mark.asyncio
    async def test_image_returns_string(self):
        """Image file returns string from OCR (may be empty for blank image)."""
        # Minimal valid PNG (1x1 pixel)
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n\x2a\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        f = UploadFile(filename="note.png", file=BytesIO(png_bytes))
        result = await extract_text_from_upload(f)
        assert isinstance(result, str)


class TestAllowedExtensionsConstant:
    """Sanity check for ALLOWED_EXTENSIONS."""

    def test_contains_expected(self):
        assert ALLOWED_EXTENSIONS == frozenset({".txt", ".pdf", ".jpg", ".jpeg", ".png"})
