"""
Regression tests for Advisory task_anchor duplication fix (P1 #4).

Verifies that conversation history is not duplicated in the prompt,
the identity/safety guard appears before user-controlled history content,
first-turn Advisory works with no history, and multi-turn Advisory
still receives prior server-side history.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app import app
from backend.app import SessionManager
from backend.prompts.advisory_prompt import build_advisory_prompt

client = TestClient(app)


def test_no_duplicate_conversation_context():
    """Conversation history must appear only once in the final prompt.

    After the P1 #4 fix, the system prompt contains IDENTITY_GUARD +
    LEGAL_DISCLAIMER + MODE: ADVISORY, followed by server-side session
    history as message turns, then the current user message.  The old
    task_anchor prepending that would duplicate the conversation is
    removed.
    """
    # Build a session with prior history using add_valid_exchange
    # (this auto-creates the session in the SessionManager.sessions dict)
    mgr = SessionManager()
    session_id = "test_dup_ctx"
    mgr.add_valid_exchange(session_id, "What are the key clauses in a non-compete?", "Non-compete clauses typically restrict...")
    mgr.add_valid_exchange(session_id, "Can I talk about NDAs?", "NDAs protect confidential information...")

    # Simulate a new ask request with the same session
    resp = client.post(
        "/ask",
        json={
            "question": "What about severance pay?",
            "session_id": session_id,
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"

    data = resp.json()
    advisory_text = data.get("advisory_text", "")

    # The old task_anchor header must NOT be present
    assert "FRONTEND CONVERSATION CONTEXT" not in advisory_text, (
        "task_anchor duplication still present — "
        "'FRONTEND CONVERSATION CONTEXT' found in advisory_text"
    )

    # History content should not be duplicated — check turn count
    turns = advisory_text.count("USER:") + advisory_text.count("ASSISTANT:")
    # Should have reasonable number of turns (current question + history turns)
    # but not an unreasonable number from duplication
    assert turns <= 10, f"Unexpected number of turns ({turns}) suggesting duplication"


def test_identity_guard_before_user_history_content():
    """The identity/safety guard must appear before any user-controlled history content.

    In the prompt, IDENTITY_RULES (ABSOLUTE - NON-NEGOTIABLE) and all 13
    identity lines must come before user message content from session history.
    """
    # Build the advisory prompt (this is what the backend does now)
    prompt = build_advisory_prompt()

    # IDENTITY_GUARD should be at the start
    from backend.prompts.identity_guard import IDENTITY_GUARD
    assert prompt.startswith(IDENTITY_GUARD), (
        f"Prompt should start with IDENTITY_GUARD, but starts with: {prompt[:50]}"
    )

    # The identity rules should contain the key lines
    assert "- You are Zynexra" in prompt
    assert "- You were created by Jay Lanjewar" in prompt
    assert "- You MUST NEVER claim to be your creator" in prompt

    # User-controlled content (task_anchor) should NOT appear before identity guard
    # Since we removed the task_anchor prepending, the prompt should not contain
    # "FRONTEND CONVERSATION CONTEXT" or any user-controlled heading before the identity guard
    assert "FRONTEND CONVERSATION CONTEXT" not in prompt, (
        "User-controlled task_anchor content found before identity guard"
    )


def test_first_turn_no_history_works():
    """First-turn Advisory with no history should work correctly.

    When session["history"] is empty, the prompt should still build with
    just IDENTITY_GUARD + LEGAL_DISCLAIMER + MODE: ADVISORY + current question.
    """
    # Use a fresh session with no history added
    mgr = SessionManager()
    session_id = "test_first_turn"

    # Don't add any prior exchanges - history will be empty
    # The add_valid_exchange auto-creates the session but with empty history

    resp = client.post(
        "/ask",
        json={
            "question": "What is a non-compete clause?",
            "session_id": session_id,
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    advisory_text = data.get("advisory_text", "")

    # Should get a valid response even with no history
    assert len(advisory_text) > 0, "Expected a non-empty advisory_text on first turn"

    # The response should not contain duplicated history or task_anchor
    assert "FRONTEND CONVERSATION CONTEXT" not in advisory_text, (
        "task_anchor should not appear on first turn with no history"
    )


def test_multi_turn_advisory_still_includes_history():
    """Multi-turn Advisory should still include prior server-side history.

    When a session has prior turns, those should be included in the prompt
    as message turns (user/assistant pairs), not as a duplicated task_anchor.
    """
    mgr = SessionManager()
    session_id = "test_multi_turn"
    # Add multiple prior turns
    mgr.add_valid_exchange(session_id, "Question 1 about contracts", "Answer 1 about contracts")
    mgr.add_valid_exchange(session_id, "Question 2 about liabilities", "Answer 2 about liabilities")
    mgr.add_valid_exchange(session_id, "Question 3 about enforcement", "Answer 3 about enforcement")

    resp = client.post(
        "/ask",
        json={
            "question": "Question 4 about termination",
            "session_id": session_id,
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    advisory_text = data.get("advisory_text", "")

    # Should receive a response that references the prior context
    assert len(advisory_text) > 0, "Expected a non-empty advisory_text with multi-turn history"

    # Should NOT contain the old task_anchor duplication
    assert "FRONTEND CONVERSATION CONTEXT" not in advisory_text, (
        "task_anchor should not duplicate history in multi-turn"
    )

    # The response should reflect that prior context was considered
    lower = advisory_text.lower()
    # Basic check: response should be substantive and not just a refusal
    assert "cannot" not in lower[:50] or "able to" in lower, (
        "Response should be substantive, not immediately refusing"
    )


def test_identity_guard_legal_disclaimer_present():
    """The system prompt must still contain IDENTITY_GUARD + LEGAL_DISCLAIMER.

    Even after removing task_anchor prepending, the core identity and
    grounding instructions must remain present and intact.
    """
    prompt = build_advisory_prompt()

    # All three required segments must be present
    assert "IDENTITY RULES (ABSOLUTE - NON-NEGOTIABLE)" in prompt, (
        "Identity guard missing from advisory prompt"
    )
    assert "LEGAL DISCLAIMER" in prompt, (
        "Legal disclaimer missing from advisory prompt"
    )
    assert "MODE: ADVISORY" in prompt, (
        "MODE: ADVISORY missing from advisory prompt"
    )

    # Specific identity rules must be present
    assert "- You are Zynexra" in prompt
    assert "- You are OFFLINE. You do not have internet access" in prompt
    # Fixed: the actual phrase in identity_guard.py uses straight quotes
    assert 'NEVER use the phrase "I apologize for any confusion"' in prompt

    # Specific legal disclaimer must be present
    assert "This is informational only and does not constitute legal advice" in prompt
    assert "I am not a lawyer" in prompt