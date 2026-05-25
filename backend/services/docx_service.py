from io import BytesIO

from fastapi import HTTPException
import docx

from backend.logger import logger


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file in memory."""
    try:
        doc = docx.Document(BytesIO(file_bytes))
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        return text
    except Exception as e:
        logger.error("DOCX extraction failed: %s", e)
        raise HTTPException(400, f"DOCX processing error: {str(e)}")
