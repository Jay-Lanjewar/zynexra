from backend.prompts.advisory_prompt import build_advisory_prompt
from backend.prompts.audit_prompt import build_audit_prompt
from backend.prompts.redaction_prompt import build_redaction_prompt


def build_execution_prompt(mode: str) -> str:
    """Route to isolated prompt builders based on execution mode."""
    if mode == "AUDIT":
        return build_audit_prompt()
    elif mode == "REDACTION":
        return build_redaction_prompt()
    elif mode == "ADVISORY":
        return build_advisory_prompt()
    else:
        # Default to AUDIT for any unknown or default mode
        return build_audit_prompt()
