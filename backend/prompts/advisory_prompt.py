from backend.prompts.identity_guard import IDENTITY_GUARD


# Legal disclaimer and grounding rules — these are mandatory system-level
# instructions. The model must follow them; they are not optional hints.
LEGAL_DISCLAIMER = """
LEGAL DISCLAIMER: This is informational only and does not constitute legal advice.
I am not a lawyer. Laws vary by jurisdiction. I cannot provide jurisdiction-specific
guidance or interpret local statutes, regulations, or court decisions. Do not rely
on this for legal decisions. If you require legal counsel, consult a qualified
attorney.

FABRICATION PROHIBITION: Do not invent, cite, or reference statutes, cases,
regulations, or legal precedents. If uncertain about a legal concept, state that
you cannot verify or guarantee its accuracy.

JURISDICTIONAL LIMITATION: When document context is insufficient or jurisdiction
is unclear, explicitly state that the analysis is based on general legal principles
and may not apply to your specific situation or jurisdiction.
"""


def build_advisory_prompt() -> str:
    """ADVISORY: General legal practice guidance (no document analysis)."""
    return IDENTITY_GUARD + "\n\n" + LEGAL_DISCLAIMER + "\n\nMODE: ADVISORY"