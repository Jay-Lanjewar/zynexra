import re


def pre_redact_pii(text: str) -> str:
    """Deterministically redact obvious PII before model invocation."""
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+.[a-zA-Z]+")
    phone_pattern = re.compile(r"\+?\d[\d\s-]{7,}")
    name_pattern = re.compile(r"[A-Z][a-z]+\s[A-Z][a-z]+")
    address_pattern = re.compile(
        r"\d+\s+[A-Za-z]+\s+(Street|St|Road|Rd|Terrace|Avenue|Ave|Lane|Ln|Drive|Dr|Boulevard|Blvd)",
        re.IGNORECASE,
    )

    text = name_pattern.sub("[REDACTED]", text)
    text = email_pattern.sub("[REDACTED]", text)
    text = phone_pattern.sub("[REDACTED]", text)
    text = address_pattern.sub("[REDACTED]", text)
    return text
