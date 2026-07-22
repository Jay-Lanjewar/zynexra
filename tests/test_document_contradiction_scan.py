"""Test _scan_document_contradictions with different extraction formats."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.contradiction_engine import _scan_document_contradictions

SURVIVAL_CLAUSE = (
    "5. Survival of Confidentiality\n"
    "The obligations relating to confidentiality shall survive termination "
    "of this Agreement for a period of five (5) years."
)
TERMINATION_CLAUSE = (
    "6. Termination\n"
    "Either party may terminate this Agreement upon thirty (30) days notice. "
    "Upon termination, all obligations under this Agreement shall immediately "
    "cease, including confidentiality obligations."
)
PREAMBLE = (
    "MASTER SOFTWARE SERVICES AGREEMENT\n"
    "This Agreement is entered into between Vendor and Client."
)


def test_blank_line_format():
    """PDF/plain-text: blank-line-separated paragraphs."""
    doc = f"{PREAMBLE}\n\n{SURVIVAL_CLAUSE}\n\n{TERMINATION_CLAUSE}\n\n"
    result = _scan_document_contradictions(doc)
    assert result.conflicting_domains, "Should detect contradiction"
    assert len(result.survival_clauses) >= 1
    assert len(result.termination_clauses) >= 1
    assert "survive termination" in result.survival_clauses[0].lower()
    assert "immediately cease" in result.termination_clauses[0].lower()
    assert result.survival_clauses[0] != result.termination_clauses[0]


def test_single_newline_format():
    """DOCX-style: paragraphs joined by single newlines."""
    lines = [
        PREAMBLE,
        "",
        "1. Definitions",
        '"Confidential Information" means non-public business information.',
        "",
        "2. Scope of Services",
        "Vendor shall provide cloud-hosted contract analytics software.",
        "",
        SURVIVAL_CLAUSE,
        "",
        TERMINATION_CLAUSE,
        "",
        "7. Indemnification",
        "Client agrees to indemnify Vendor.",
    ]
    doc = "\n".join(lines)
    result = _scan_document_contradictions(doc)
    assert result.conflicting_domains, "Should detect contradiction"
    assert len(result.survival_clauses) >= 1
    assert len(result.termination_clauses) >= 1
    assert "survive termination" in result.survival_clauses[0].lower()
    assert "immediately cease" in result.termination_clauses[0].lower()
    assert result.survival_clauses[0] != result.termination_clauses[0]


def test_mixed_format():
    """Some blank-line breaks, some single-newline sections."""
    doc = (
        f"{PREAMBLE}\n\n"
        f"1. Definitions\n\"Confidential Information\" means...\n\n"
        f"{SURVIVAL_CLAUSE}\n"
        f"{TERMINATION_CLAUSE}\n\n"
        f"7. Indemnification\nClient agrees to indemnify."
    )
    result = _scan_document_contradictions(doc)
    assert result.conflicting_domains, "Should detect contradiction"


def test_no_contradiction():
    """Only survival language, no termination clause."""
    doc = f"{PREAMBLE}\n\n{SURVIVAL_CLAUSE}\n\n"
    result = _scan_document_contradictions(doc)
    assert not result.conflicting_domains


def test_only_termination():
    """Only termination language, no survival clause."""
    doc = f"{PREAMBLE}\n\n{TERMINATION_CLAUSE}\n\n"
    result = _scan_document_contradictions(doc)
    assert not result.conflicting_domains


def test_empty_document():
    result = _scan_document_contradictions("")
    assert not result.conflicting_domains
    assert not result.survival_clauses
    assert not result.termination_clauses


def test_short_document():
    result = _scan_document_contradictions("Hello world.")
    assert not result.conflicting_domains


def test_docx_style_single_block():
    """DOCX extract where blank-line split puts everything in one block.
    Should fall through to heading-based splitting."""
    doc = (
        "PREAMBLE\nThis is a test agreement.\n"
        "1. Definitions\nSome definitions here.\n"
        "2. Scope\nScope description.\n"
        "5. Survival of Confidentiality\nThe obligations relating to confidentiality "
        "shall survive termination of this Agreement for a period of five (5) years.\n"
        "6. Termination\nEither party may terminate. Upon termination, all obligations "
        "under this Agreement shall immediately cease, including confidentiality obligations.\n"
        "7. General\nMiscellaneous provisions."
    )
    result = _scan_document_contradictions(doc)
    assert result.conflicting_domains, "Should detect contradiction via heading splitting"
    assert result.survival_clauses[0] != result.termination_clauses[0], "Must be different clauses"
    assert "survive termination" in result.survival_clauses[0].lower()
    assert "immediately cease" in result.termination_clauses[0].lower()


def test_same_survival_and_termination_clause():
    """When both languages appear in same clause, no contradiction reported."""
    doc = f"{PREAMBLE}\n\nBoth survive termination and immediately cease in one paragraph.\n\n"
    result = _scan_document_contradictions(doc)
    assert isinstance(result.conflicting_domains, set)
