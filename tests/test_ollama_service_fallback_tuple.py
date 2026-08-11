"""
Regression tests for the generate_response() tuple-contract fix.

The OllamaService.generate_response() method previously returned
(text, analysis_metadata, fallback_used) even though its type hint and
docstring declared (text, fallback_used, analysis_metadata). Callers in
response_generator.py and app.py unpack the second and third values in the
declared order, so a successful primary-model response would place a
truthy analysis_metadata dict in the fallback_used slot, falsely reporting
fallback_used=True.

These tests verify the actual return order matches the declared contract:
    (response_text, fallback_used, analysis_metadata)

Pure unit tests with no Ollama dependency (model layer is mocked).
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi import HTTPException

from backend.services.ollama_service import OllamaService
from backend.engines.response_generator import ResponseGenerator


def _sample_metadata():
    return {
        "was_truncated": False,
        "kept_chars": 3207,
        "dropped_chars": 0,
        "context_utilization_pct": 61.5,
        "pages_seen": 5,
    }


def _sample_messages():
    return [{"role": "user", "content": "test contract text"}]


# --- OllamaService contract -------------------------------------------------


def test_success_path_returns_false_fallback_and_preserves_metadata():
    svc = OllamaService()
    metadata = _sample_metadata()
    with patch.object(svc, "_generate_with_model", return_value=("raw output", metadata)) as gen:
        response_text, fallback_used, analysis_metadata = svc.generate_response(
            _sample_messages(), "qwen2.5:3b-instruct", "AUDIT"
        )
    gen.assert_called_once()
    assert response_text == "raw output"
    assert fallback_used is False
    assert analysis_metadata == metadata


def test_success_path_metadata_is_not_truthy_in_fallback_slot():
    svc = OllamaService()
    with patch.object(svc, "_generate_with_model", return_value=("raw", _sample_metadata())):
        _, fallback_used, _ = svc.generate_response(_sample_messages(), "model", "AUDIT")
    assert fallback_used is False
    assert fallback_used is not True


def test_fallback_path_returns_true_fallback_and_fallback_metadata():
    svc = OllamaService()
    fallback_metadata = {"was_truncated": True, "kept_chars": 100, "dropped_chars": 0, "context_utilization_pct": 10.0, "pages_seen": None}

    def _flaky_generate(messages, model, mode, document_meta=None):
        if model == "primary-model":
            raise HTTPException(500, "Model communication error: something")
        return ("fallback raw", fallback_metadata)

    from backend.config import settings

    with patch.object(svc, "_generate_with_model", side_effect=_flaky_generate):
        response_text, fallback_used, analysis_metadata = svc.generate_response(
            _sample_messages(), "primary-model", "AUDIT"
        )
    assert response_text == "fallback raw"
    assert fallback_used is True
    assert analysis_metadata == fallback_metadata
    assert analysis_metadata.get("was_truncated") is True


def test_rethrows_when_fallback_not_warranted():
    svc = OllamaService()

    def _fail_once(messages, model, mode, document_meta=None):
        raise HTTPException(400, "bad request")

    with patch.object(svc, "_generate_with_model", side_effect=_fail_once):
        with pytest.raises(HTTPException):
            svc.generate_response(_sample_messages(), "primary-model", "AUDIT")


# --- ResponseGenerator pass-through -----------------------------------------


def test_response_generator_preserves_contract():
    rg = ResponseGenerator()
    metadata = _sample_metadata()
    with patch.object(
        rg.ollama_service,
        "generate_response",
        return_value=("raw output", False, metadata),
    ) as gen:
        response_text, fallback_used, analysis_metadata = rg.generate_response(
            _sample_messages(), "qwen2.5:3b-instruct", "AUDIT"
        )
    gen.assert_called_once()
    assert response_text == "raw output"
    assert fallback_used is False
    assert analysis_metadata == metadata
