import re
from typing import Optional, Tuple
import time

import numpy as np
from fastapi import HTTPException
import pymupdf

from backend.config import settings
from backend.engines.input_quality_engine import assess_input_quality
from backend.logger import logger


_ocr_engine = None


def _get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr import RapidOCR
        # PP-OCRv6 defaults (use_dilation=True, unclip_ratio=1.6) are optimal for
        # English legal text per ablation study. Higher unclip_ratio degrades word
        # recall (86.7% at 2.0 vs 93.9% at 1.6) by merging nearby detection boxes.
        _ocr_engine = RapidOCR()
    return _ocr_engine


def _fix_merged_words(text: str) -> str:
    """Insert missing spaces at reliably detectable word boundaries."""
    text = re.sub(r'(?<=[a-zA-Z0-9])\.(?=[A-Z])', '. ', text)
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    return text


def _ocr_page(page) -> str:
    try:
        pix = page.get_pixmap(dpi=settings.OCR_DPI)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        engine = _get_ocr_engine()
        result = engine(img)
        if result.txts:
            return "\n".join(_fix_merged_words(t) for t in result.txts) + "\n"
        return ""
    except Exception as e:
        logger.warning("[OCRFallback] OCR failed for page: %s", e)
        return page.get_text()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text, _ = extract_text_from_pdf_with_stats(file_bytes)
    return text


def _pyMuPDF_extract_all(doc) -> list[str]:
    return [page.get_text() for page in doc]


def _ocr_deficient_pages(doc, page_texts, deficient_indices) -> list[str]:
    for idx in deficient_indices:
        page_texts[idx] = _ocr_page(doc[idx])
    return page_texts


def extract_text_from_pdf_with_stats(file_bytes: bytes) -> Tuple[str, Optional[int]]:
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        pages_seen = len(doc)

        if not settings.OCR_ENABLED or pages_seen == 0:
            return "".join([page.get_text() for page in doc]), pages_seen

        page_texts = _pyMuPDF_extract_all(doc)

        deficient_indices = [
            i for i, t in enumerate(page_texts)
            if len(t.strip()) < settings.OCR_MIN_CHARS_PER_PAGE
        ]

        if not deficient_indices:
            return "".join(page_texts), pages_seen

        ocr_count = len(deficient_indices)
        bad_ratio = ocr_count / max(pages_seen, 1)
        logger.info(
            "[OCRFallback] total_pages=%d deficient=%d ratio=%.2f",
            pages_seen, ocr_count, bad_ratio,
        )

        ocr_start = time.time()
        page_texts = _ocr_deficient_pages(doc, page_texts, deficient_indices)
        ocr_duration = time.time() - ocr_start
        logger.info(
            "[OCRFallback] ocr_pages=%d duration=%.2fs",
            ocr_count, ocr_duration,
        )

        text = "".join(page_texts)

        quality = assess_input_quality(text)
        if quality.is_degraded and bad_ratio < settings.OCR_BAD_PAGE_RATIO:
            logger.warning(
                "[OCRFallback] still_degraded after_page_ocr score=%.2f bad_ratio=%.2f",
                quality.score, bad_ratio,
            )
            full_start = time.time()
            ocr_texts = [_ocr_page(page) for page in doc]
            text = "".join(ocr_texts)
            logger.info(
                "[OCRFallback] full_doc_ocr pages=%d duration=%.2fs",
                pages_seen, time.time() - full_start,
            )

        return text, pages_seen

    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        raise HTTPException(400, f"PDF processing error: {str(e)}")
