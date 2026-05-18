from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class ValidationResult:
    """Result of response validation containing validation status and details."""
    is_valid: bool
    violation_type: Optional[str] = None
    violation_reason: Optional[str] = None
    refusal_message: Optional[str] = None


@dataclass
class ValidationContext:
    """Context information needed for response validation."""
    user_input: str
    session_mode: str
    is_creator_question: bool


class ValidationEngine:
    """Validates complete responses without triggering regeneration."""

    def __init__(self):
        # Detect only first-person AI identity disclosures.
        # This intentionally allows neutral/academic terminology such as "language model".
        self.identity_disclosure_patterns = [
            re.compile(
                r"\b(?:as\s+an?\s+|i\s*(?:am|'m)\s+an?\s+)"
                r"(?:ai|artificial\s+intelligence|language\s+model|llm|chatbot|assistant)\b",
                re.IGNORECASE
            ),
            re.compile(
                r"\b(?:i\s*(?:am|'m)\s+)(?:a\s+)?(?:large\s+)?language\s+model\b",
                re.IGNORECASE
            ),
            re.compile(
                r"\b(?:i\s+was\s+(?:created|built|trained)\s+as\s+an?\s+)"
                r"(?:ai|assistant|language\s+model)\b",
                re.IGNORECASE
            ),
        ]

    def validate_response(self, response: str, context: ValidationContext) -> ValidationResult:
        """Validate complete response against all rules.

        Args:
            response: Complete response string to validate
            context: Validation context with user input and session info

        Returns:
            ValidationResult with validation status and details
        """
        try:
            # Input validation
            if not response or not isinstance(response, str):
                return ValidationResult(
                    is_valid=False,
                    violation_type="validation_error",
                    violation_reason="Invalid response format for validation",
                    refusal_message="[SYSTEM ERROR] Response validation failed due to invalid format."
                )

            response_lower = response.lower()

            # 1. Identity Check (Creator Name Integrity)
            if "lanjewar" in context.user_input.lower() and "jay" not in response_lower:
                return ValidationResult(
                    is_valid=False,
                    violation_type="identity_guard",
                    violation_reason="Identity guard failure: Must state creator exactly.",
                    refusal_message="[SYSTEM REFUSAL] Response rejected due to identity guard violation."
                )

            # 2. First-person AI identity disclosure check
            for pattern in self.identity_disclosure_patterns:
                if pattern.search(response):
                    return ValidationResult(
                        is_valid=False,
                        violation_type="identity_disclosure",
                        violation_reason=f"Contains first-person AI identity disclosure matching pattern: '{pattern.pattern}'",
                        refusal_message="[SYSTEM REFUSAL] Response rejected due to compliance violation: First-person AI identity disclosure detected."
                    )

            return ValidationResult(is_valid=True)

        except Exception as e:
            # Graceful handling of validation engine failures
            return ValidationResult(
                is_valid=False,
                violation_type="validation_error",
                violation_reason=f"Validation engine error: {str(e)}",
                refusal_message="[SYSTEM ERROR] Response validation failed due to internal error."
            )

    def get_refusal_message(self, violation_type: str, reason: str) -> str:
        """Generate appropriate refusal message for violation with optimized performance.

        Args:
            violation_type: Type of validation violation
            reason: Specific reason for the violation

        Returns:
            Formatted refusal message (returned immediately)
        """
        # Pre-formatted refusal messages for immediate return - no processing delays
        return f"[SYSTEM REFUSAL] Response rejected due to compliance violation: {reason}."
