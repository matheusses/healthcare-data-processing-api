"""Extract text from uploaded note files: .txt, .pdf, and images (jpg, png) via OCR."""

import logging
import tempfile


from app.config import settings
from app.shared.exceptions import DomainException
from app.shared.interfaces.document_loading.extractor import IDocumentExtractor


logger = logging.getLogger(__name__)



class DocumentExtractor(IDocumentExtractor):
    """Extract text from uploaded note files: .txt, .pdf, and images (jpg, png) via OCR."""

    
    async def extract_text_from_upload(self, raw: bytes, content_type: str) -> str:
        """
        Read the uploaded file and extract plain text.
        - .txt: decode as UTF-8.
        - .pdf: PyPDFLoader (LangChain), concatenate page text.
        - .jpg / .jpeg / .png: RapidOCR, return extracted text (handwritten supported).

        Raises DomainException if extraction fails (e.g. corrupted PDF).
        """
        if content_type not in settings.allowed_content_types_list:
            raise DomainException(f"Unsupported file type: {content_type}.", code="INVALID_FILE_TYPE")

        match content_type:
            case "text/plain":
                return raw.decode("utf-8", errors="replace")
            case "application/pdf":
                return self._extract_text_from_pdf(raw)
            case "image/jpeg" | "image/jpg" | "image/png":
                return self._extract_text_from_image(raw)
            case _:
                raise DomainException(f"Unsupported file type: {content_type}.", code="INVALID_FILE_TYPE")


    def _extract_text_from_pdf(self, raw: bytes) -> str:
        """Extract text from PDF bytes using LangChain PyPDFLoader (temp file)."""
        try:
            from langchain_community.document_loaders import PyPDFLoader
        except ImportError as e:
            logger.warning("PyPDFLoader not available: %s", e)
            raise DomainException("PDF extraction not available.", code="EXTRACTION_ERROR") from e

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(raw)
            tmp.flush()
            loader = PyPDFLoader(tmp.name)
            docs = loader.load()
        if not docs:
            return ""
        return "\n\n".join(d.page_content for d in docs if d.page_content).strip()


    def _extract_text_from_image(self, raw: bytes) -> str:
        """Extract text from image bytes using RapidOCR (handwritten supported)."""
        try:
            from langchain_community.document_loaders.parsers.pdf import extract_from_images_with_rapidocr
        except ImportError as e:
            logger.warning("RapidOCR not available: %s", e)
            raise DomainException("Image OCR not available.", code="EXTRACTION_ERROR") from e

        try:
            text = extract_from_images_with_rapidocr([raw])
        except Exception as e:
            logger.warning("RapidOCR extraction failed: %s", e)
            raise DomainException(
                "Could not extract text from image (OCR failed).",
                code="EXTRACTION_ERROR",
            ) from e
        return (text or "").strip()

    
