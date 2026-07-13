"""Create test PDFs for OCR fallback testing."""
import io

import pymupdf
from PIL import Image, ImageDraw


def make_image_based_page(doc, text_lines, width=1240, height=1754, page_width=595, page_height=842):
    """Create a page that simulates a scanned document (image with text)."""
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = 100
    for line in text_lines:
        draw.text((100, y), line, fill="black")
        y += 50
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    pix = pymupdf.Pixmap(buf.getvalue())
    page = doc.new_page(width=page_width, height=page_height)
    page.insert_image(page.rect, pixmap=pix)


# 1. Searchable PDF (3 pages with text)
doc = pymupdf.open()
for i in range(3):
    page = doc.new_page()
    page.insert_text(
        (72, 100),
        f"This is searchable page {i+1} of the test document. It contains"
        f" sufficient text to avoid OCR fallback, with multiple sentences"
        f" to exceed the 50-character threshold easily.",
    )
doc.save("tests/test_documents/test_searchable.pdf")
doc.close()
print("Created searchable PDF")


# 2. Scanned PDF (2 image-based pages with legal text)
doc = pymupdf.open()
make_image_based_page(
    doc,
    [
        "CONFIDENTIALITY AGREEMENT",
        "",
        "This Confidentiality Agreement (the Agreement) is entered into as of",
        "July 1, 2026, by and between Acme Corporation (Discloser) and",
        "Beta Industries, Inc. (Recipient).",
        "",
        "1. DEFINITION OF CONFIDENTIAL INFORMATION.",
        "Confidential Information means any information disclosed by Discloser",
        "to Recipient that is marked as confidential or that a reasonable",
        "person would understand to be confidential under the circumstances.",
        "",
        "2. OBLIGATIONS OF RECIPIENT.",
        "Recipient shall maintain the Confidential Information in strict",
        "confidence and shall not disclose it to any third party without",
        "the prior written consent of Discloser.",
    ],
)
make_image_based_page(
    doc,
    [
        "3. TERM AND TERMINATION.",
        "This Agreement shall terminate five (5) years from the Effective Date.",
        "The confidentiality obligations shall survive termination for a",
        "period of three (3) years.",
        "",
        "4. LIMITATION OF LIABILITY.",
        "Neither party shall be liable for any indirect, incidental, or",
        "consequential damages arising out of this Agreement. The aggregate",
        "liability of either party shall not exceed $100,000.",
    ],
)
doc.save("tests/test_documents/test_scanned.pdf")
doc.close()
print("Created scanned PDF (image-based)")


# 3. Mixed PDF (2 digital + 2 image-based)
doc = pymupdf.open()
for i in range(2):
    page = doc.new_page()
    page.insert_text(
        (72, 100),
        f"This is digital page {i+1} with plenty of text content for"
        f" testing the mixed PDF scenario with OCR fallback.",
    )
make_image_based_page(
    doc,
    [
        "SCHEDULE A: PRICING",
        "",
        "Item                      Quantity     Unit Price",
        "License Fee               1            $50,000",
        "Maintenance               3 years      $15,000",
        "Implementation            1            $10,000",
        "",
        "Total: $75,000",
    ],
)
make_image_based_page(
    doc,
    [
        "SCHEDULE B: DELIVERABLES",
        "",
        "1. Software installation and configuration",
        "2. User training (up to 20 users)",
        "3. Documentation package",
        "4. Source code escrow",
    ],
)
doc.save("tests/test_documents/test_mixed.pdf")
doc.close()
print("Created mixed PDF")
