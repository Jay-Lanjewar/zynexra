from fastapi import HTTPException
import pymupdf

from backend.logger import logger


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file in memory."""
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        raise HTTPException(400, f"PDF processing error: {str(e)}")
