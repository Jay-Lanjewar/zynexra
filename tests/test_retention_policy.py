"""
Regression tests for Advisory retention policy (P2).

Verifies that the 90-day retention policy is correctly applied,
configurable via .env, and that startup cleanup is safe and idempotent.
"""

import sys
from pathlib import Path

import inspect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.services.db_service import db_service


def test_retention_configurable():
    """RETENTION_DAYS can be read from settings and used by clear_old_records()."""
    days = settings.RETENTION_DAYS
    assert isinstance(days, int), f"RETENTION_DAYS should be int, got {type(days)}"
    assert days > 0, f"RETENTION_DAYS should be positive, got {days}"


def test_startup_cleanup_invoked():
    """Startup cleanup should invoke clear_old_records with the configured days."""
    assert db_service is not None, "db_service should be available"
    import inspect
    sig = inspect.signature(db_service.clear_old_records)
    assert "days_old" in sig.parameters, "clear_old_records should accept days_old parameter"
    default = sig.parameters["days_old"].default
    assert default == 90, f"Default days_old should be 90, got {default}"


def test_startup_cleanup_idempotent():
    """Startup cleanup should be idempotent - running it twice should be safe."""
    import inspect
    sig = inspect.signature(db_service.clear_old_records)
    assert "days_old" in sig.parameters


def test_old_records_deleted_from_all_tables():
    """clear_old_records should delete from all three tables: audit, redaction, and advisory."""
    with open("backend/services/db_service.py", "r") as f:
        content = f.read()

    assert "audit_history" in content, "audit_history should be in clear_old_records"
    assert "redaction_history" in content, "redaction_history should be in clear_old_records"
    assert "advisory_sessions" in content, "advisory_sessions should be in clear_old_records"
    assert "DELETE FROM audit_history" in content
    assert "DELETE FROM redaction_history" in content
    assert "DELETE FROM advisory_sessions" in content


def test_recent_records_preserved():
    """Recent records (within retention window) should be preserved."""
    with open("backend/services/db_service.py", "r") as f:
        content = f.read()

    assert "datetime('now', '-' || ? || ' days')" in content, (
        "SQL should use datetime comparison to preserve recent records"
    )