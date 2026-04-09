"""Tests for core.audit.checks module."""

import pytest
from core.audit.checks import AUDIT_CHECKS


def test_audit_checks_not_empty():
    """Verify that audit checks are defined."""
    assert len(AUDIT_CHECKS) > 0


def test_all_checks_have_required_fields():
    """Verify every check has all required fields."""
    required_fields = ["id", "title", "description", "query", "severity", "source_table", "analysis_method"]

    for check in AUDIT_CHECKS:
        for field in required_fields:
            assert field in check, f"Check {check.get('id', 'unknown')} missing field: {field}"


def test_check_ids_are_unique():
    """Verify all check IDs are unique."""
    ids = [c["id"] for c in AUDIT_CHECKS]
    assert len(ids) == len(set(ids)), "Duplicate check IDs found"


def test_severity_values_valid():
    """Verify all severities are valid values."""
    valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    for check in AUDIT_CHECKS:
        assert check["severity"] in valid_severities, \
            f"Check {check['id']} has invalid severity: {check['severity']}"


def test_analysis_method_values_valid():
    """Verify all analysis_method values are valid."""
    valid_methods = {"SQL_CHECK", "LLM_ANALYSIS"}

    for check in AUDIT_CHECKS:
        assert check["analysis_method"] in valid_methods, \
            f"Check {check['id']} has invalid analysis_method: {check['analysis_method']}"


def test_queries_are_non_empty():
    """Verify all queries are non-empty strings."""
    for check in AUDIT_CHECKS:
        assert check["query"].strip(), f"Check {check['id']} has empty query"


def test_queries_end_with_valid_sql():
    """Verify queries look like valid SELECT statements (basic check)."""
    for check in AUDIT_CHECKS:
        query = check["query"].strip().upper()
        assert query.startswith("SELECT"), \
            f"Check {check['id']} query doesn't start with SELECT: {query[:50]}"


def test_source_tables_are_valid():
    """Verify source tables are from our schema."""
    valid_tables = {
        "decisions",
        "trades",
        "portfolios",
        "portfolio_positions",
        "memories",
        "llm_reasoning_logs",
        "newsletter_snapshots",
        "market_data_cache",
        "price_history",
        "portfolio_performance",
    }

    for check in AUDIT_CHECKS:
        assert check["source_table"] in valid_tables, \
            f"Check {check['id']} has unknown source_table: {check['source_table']}"


def test_no_orphan_trade_refs_check_exists():
    """Verify the critical orphan_trade_refs check exists."""
    check_ids = [c["id"] for c in AUDIT_CHECKS]
    assert "orphan_trade_refs" in check_ids

    check = next(c for c in AUDIT_CHECKS if c["id"] == "orphan_trade_refs")
    assert check["severity"] == "HIGH"
    assert check["analysis_method"] == "SQL_CHECK"


def test_executed_without_trade_check_exists():
    """Verify the CRITICAL executed_without_trade check exists."""
    check_ids = [c["id"] for c in AUDIT_CHECKS]
    assert "executed_without_trade" in check_ids

    check = next(c for c in AUDIT_CHECKS if c["id"] == "executed_without_trade")
    assert check["severity"] == "CRITICAL"
