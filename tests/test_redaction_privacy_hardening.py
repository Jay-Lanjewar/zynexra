"""Regression tests: P0 #3 backend privacy hardening leaks.

Verifies the three remaining privacy gaps are closed:
1. REDACTION session history stores the redacted representation, never raw input.
2. ask_file REDACTION DB write persists sanitized entities (no raw originals).
3. Rejected-PERSON debug logging no longer emits the raw candidate value.
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.engines.redaction_engine import RedactionEngine, RedactionOptions
from backend.services.db_service import DatabaseService
import backend.app as app_module

client = TestClient(app_module.app)

RAW_INPUT = "Contact John Doe at jdoe@example.com or 555-014-2211."


def _redaction_history_turns(session_id):
    return app_module.sessions.get(session_id)["history"]


def test_redaction_history_contains_no_raw_input():
    session_id = "p0-history-no-raw"
    original_available = app_module.db_service.available
    app_module.db_service.available = False
    try:
        resp = client.post("/set_mode", json={"session_id": session_id, "mode": "REDACTION"})
        assert resp.status_code == 200

        resp = client.post("/ask", json={"session_id": session_id, "question": RAW_INPUT})
        assert resp.status_code == 200
        assert "[REDACTED_" in resp.text

        turns = _redaction_history_turns(session_id)
        assert len(turns) == 1, "expected one validated REDACTION exchange in history"

        user_turn = turns[0]["user"]
        assistant_turn = turns[0]["assistant"]
        assert "John Doe" not in user_turn
        assert "jdoe@example.com" not in user_turn
        assert "555-014-2211" not in user_turn
        assert "John Doe" not in assistant_turn
        assert user_turn == assistant_turn, "history should store the redacted representation for both roles"
        assert "[REDACTED_" in user_turn
    finally:
        app_module.db_service.available = original_available


def test_ask_file_db_entity_json_contains_no_raw_originals(tmp_path):
    tmp_db = str(tmp_path / "zynexra.db")
    temp_svc = DatabaseService(db_path=tmp_db)
    original_svc = app_module.db_service
    app_module.db_service = temp_svc
    try:
        session_id = "p0-ask-file-no-raw"
        resp = client.post(
            "/ask_file",
            files={"file": ("note.txt", RAW_INPUT.encode("utf-8"), "text/plain")},
            data={"session_id": session_id, "mode": "REDACTION", "response_format": "json"},
        )
        assert resp.status_code == 200

        conn = sqlite3.connect(tmp_db)
        row = conn.execute(
            "SELECT entities_json, redaction_count FROM redaction_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None, "expected a redaction record to be persisted"
        entities_json, redaction_count = row
        assert redaction_count >= 1

        assert "John Doe" not in entities_json
        assert "jdoe@example.com" not in entities_json
        assert "555-014-2211" not in entities_json

        stored = json.loads(entities_json)
        assert isinstance(stored, dict) and stored, "expected a non-empty entity map"
        for entity in stored.values():
            assert entity.get("original_text") == entity.get("replacement")
            assert "[REDACTED_" in entity.get("replacement", "")
    finally:
        app_module.db_service = original_svc


def test_rejected_person_debug_log_does_not_emit_candidate():
    logger = logging.getLogger("zynexra")
    previous_level = logger.level
    records = []

    class Recorder(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    recorder = Recorder()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(recorder)
    try:
        engine = RedactionEngine()
        text = "This Agreement between Jane Smith and Acme Corp."
        engine.redact(text, RedactionOptions())

        rejection_messages = [
            message for message in records if "Rejected PERSON candidate" in message
        ]
        assert rejection_messages, "expected at least one rejected-PERSON debug log"

        for message in rejection_messages:
            assert "This Agreement" not in message
            assert "Jane Smith" not in message
            assert "reason=" in message, "non-sensitive reason metadata should be retained"
    finally:
        logger.removeHandler(recorder)
        logger.setLevel(previous_level)
