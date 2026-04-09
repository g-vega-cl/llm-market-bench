"""Tests for core.audit.runner module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestGenerateAuditRunId:
    """Tests for the generate_audit_run_id function."""

    def test_format_is_correct(self):
        """Verify audit run ID follows expected format."""
        from core.audit.runner import generate_audit_run_id

        run_id = generate_audit_run_id()

        assert run_id.startswith("audit-")
        parts = run_id.split("-")
        assert len(parts) == 3
        assert parts[1] == datetime.now(timezone.utc).strftime("%Y%m%d")
        assert len(parts[2]) == 6

    def test_audit_run_id_includes_timestamp(self):
        """Verify audit run ID includes timestamp that changes per second."""
        import time
        from core.audit.runner import generate_audit_run_id

        id1 = generate_audit_run_id()
        time.sleep(1.1)
        id2 = generate_audit_run_id()

        assert id1 != id2


class TestCategorizeAuditType:
    """Tests for the categorize_audit_type function."""

    def test_orphan_prefix_maps_to_db_anomaly(self):
        """Verify orphan checks are categorized as DB_ANOMALY."""
        from core.audit.runner import categorize_audit_type

        assert categorize_audit_type("orphan_trade_refs") == "DB_ANOMALY"
        assert categorize_audit_type("orphan_portfolio_trades") == "DB_ANOMALY"

    def test_executed_prefix_maps_to_db_anomaly(self):
        """Verify executed checks are categorized as DB_ANOMALY."""
        from core.audit.runner import categorize_audit_type

        assert categorize_audit_type("executed_without_trade") == "DB_ANOMALY"

    def test_invalid_prefix_maps_to_data_quality(self):
        """Verify invalid checks are categorized as DATA_QUALITY."""
        from core.audit.runner import categorize_audit_type

        assert categorize_audit_type("invalid_decision_status") == "DATA_QUALITY"

    def test_stale_prefix_maps_to_data_quality(self):
        """Verify stale checks are categorized as DATA_QUALITY."""
        from core.audit.runner import categorize_audit_type

        assert categorize_audit_type("stale_created_decisions") == "DATA_QUALITY"

    def test_empty_prefix_maps_to_data_quality(self):
        """Verify empty checks are categorized as DATA_QUALITY."""
        from core.audit.runner import categorize_audit_type

        assert categorize_audit_type("empty_reasoning") == "DATA_QUALITY"

    def test_duplicate_prefix_maps_to_data_quality(self):
        """Verify duplicate checks are categorized as DATA_QUALITY."""
        from core.audit.runner import categorize_audit_type

        assert categorize_audit_type("duplicate_positions") == "DATA_QUALITY"

    def test_unknown_prefix_maps_to_code_error(self):
        """Verify unknown check types default to CODE_ERROR."""
        from core.audit.runner import categorize_audit_type

        assert categorize_audit_type("some_other_check") == "CODE_ERROR"


class TestInsertAudit:
    """Tests for the insert_audit function."""

    def test_insert_audit_builds_correct_object(self):
        """Verify insert_audit constructs the audit object correctly."""
        from core.audit.runner import insert_audit

        mock_supabase = MagicMock()
        mock_check = {
            "id": "orphan_trade_refs",
            "title": "Orphaned Trade References",
            "description": "Decisions with invalid trade_id",
            "severity": "HIGH",
            "source_table": "decisions",
            "analysis_method": "SQL_CHECK"
        }
        mock_metadata = {"id": "abc-123"}

        insert_audit(
            supabase=mock_supabase,
            audit_run_id="audit-20260409-120000",
            check=mock_check,
            source_id="abc-123",
            metadata=mock_metadata
        )

        mock_supabase.table.assert_called_with("system_audits")
        mock_supabase.table.return_value.insert.assert_called_once()

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]

        assert call_args["audit_type"] == "DB_ANOMALY"
        assert call_args["severity"] == "HIGH"
        assert call_args["title"] == "Orphaned Trade References"
        assert call_args["status"] == "OPEN"
        assert call_args["source_table"] == "decisions"
        assert call_args["source_id"] == "abc-123"
        assert call_args["audit_run_id"] == "audit-20260409-120000"
        assert call_args["analysis_method"] == "SQL_CHECK"
        assert call_args["created_by"] == "SYSTEM"


class TestInsertLogAudit:
    """Tests for the insert_log_audit function."""

    def test_insert_log_audit_builds_correct_object(self):
        """Verify insert_log_audit constructs the audit object correctly."""
        from core.audit.runner import insert_log_audit

        mock_supabase = MagicMock()

        insert_log_audit(
            supabase=mock_supabase,
            audit_run_id="audit-20260409-120000",
            description="Analyzed 6 log files",
            suggestions="[]"
        )

        mock_supabase.table.assert_called_with("system_audits")
        mock_supabase.table.return_value.insert.assert_called_once()

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]

        assert call_args["audit_type"] == "SYSTEM_LOG"
        assert call_args["severity"] == "MEDIUM"
        assert call_args["title"] == "System Log Analysis"
        assert call_args["status"] == "OPEN"
        assert call_args["suggestion"] == "[]"
        assert call_args["audit_run_id"] == "audit-20260409-120000"
        assert call_args["analysis_method"] == "LLM_ANALYSIS"


class TestConfigure:
    """Tests for the configure function."""

    def test_configure_sets_supabase_credentials(self):
        """Verify configure sets the Supabase URL and key."""
        from core.audit.runner import configure

        configure("https://example.supabase.co", "test-key-123")

        from core.audit import runner
        assert runner.SUPABASE_URL == "https://example.supabase.co"
        assert runner.SUPABASE_SERVICE_ROLE_KEY == "test-key-123"
