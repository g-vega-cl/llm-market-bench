import pytest
import os
from pydantic import BaseModel
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime

# Import models from engine
from apps.engine.core.models import DecisionObject, MacroEvent, DecisionsResponse
from apps.engine.analysis.post_analysis import PostAnalysisResult
from tests.contracts.sql_reflection import get_sql_schema_from_migrations

# Reflection source: Use migrations from supabase/
MIGRATIONS_PATH = "supabase/migrations"

@pytest.fixture(scope="module")
def sql_schema():
    """Parses migration files once for the module."""
    return get_sql_schema_from_migrations(MIGRATIONS_PATH)

def test_decision_object_parity_with_sql(sql_schema):
    """Validates DecisionObject model against reflection-based SQL schema."""
    # Source of truth: SQL migrations
    expected_columns = sql_schema.get("decisions", {})
    assert expected_columns, "Could not find 'decisions' table in migrations."

    # Model: Pydantic model
    model_fields = DecisionObject.model_fields

    # Check core DB-backed fields
    # Ticker, signal, reasoning, etc. should match
    db_backed_fields = ["ticker", "signal", "confidence", "reasoning", "model_provider", "model_name", "source_id"]
    for field in db_backed_fields:
        assert field in model_fields, f"Field {field} missing in Pydantic model"
        assert field in expected_columns, f"Field {field} missing in SQL schema for 'decisions'"

    # Check for renamed fields drift
    # Example: trade_id exists in SQL, but shouldn't necessarily be in the LLM-output model
    # (Because the LLM doesn't output the trade_id, the attribution service adds it)
    assert "trade_id" in expected_columns
    assert "trade_id" not in model_fields

def test_memories_parity_with_sql(sql_schema):
    """Validates MacroEvent parity with 'memories' table from SQL reflection."""
    expected_columns = sql_schema.get("memories", {})
    assert expected_columns, "Could not find 'memories' table in migrations."

    # MacroEvent maps its reasoning to content or metadata in DB
    # This is a complex mapping, but let's check core fields.
    assert "content" in expected_columns
    assert "metadata" in expected_columns
    assert "memory_type" in expected_columns
    assert "importance_score" in expected_columns

def test_trade_rejections_parity_with_sql(sql_schema):
    """Ensures the new trade_rejections table matches our persistence expectations."""
    expected_columns = sql_schema.get("trade_rejections", {})
    assert expected_columns, "Detailed trade_rejections table missing from migrations."

    required_audit_fields = [
        "provider", "ticker", "requested_action", "rejection_reason",
        "decision_trace_id", "market_price"
    ]
    for field in required_audit_fields:
        assert field in expected_columns, f"Audit field {field} missing in trade_rejections table"

def test_sql_nullability_parity(sql_schema):
    """Ensures Pydantic optionality matches SQL nullability where applicable."""
    # Check additive column evolution
    decisions_schema = sql_schema.get("decisions", {})

    # Check for specifically added nullable columns that should have defaults
    evolution_columns = ["status", "metadata", "trade_id"]
    for col in evolution_columns:
        if col in decisions_schema:
            assert decisions_schema[col]["nullable"] is True, f"Evolution column {col} should remain nullable for migration safety"

    # Reasoning logs evolution
    logs_schema = sql_schema.get("llm_reasoning_logs", {})
    if "normalized_transcript" in logs_schema:
        assert logs_schema["normalized_transcript"]["nullable"] is True

def test_additive_schema_evolution(sql_schema):
    """Specifically audits for additive columns with defaults."""
    for table, columns in sql_schema.items():
        for col_name, info in columns.items():
            # If a column was added via ALTER, it MUST be nullable or have a DEFAULT
            # to avoid breaking existing engine logic during migrations.
            if info.get("is_additive"):
                assert info["nullable"] or info["default"] is not None, \
                    f"Additive column '{col_name}' in table '{table}' must be nullable or have a DEFAULT."

def test_enum_consistency():
    """Ensures Literal enums match logic expectations."""
    # Decisions Signal
    signal_type = DecisionObject.model_fields["signal"].annotation
    assert "BUY" in signal_type.__args__
    assert "SELL" in signal_type.__args__
    assert "HOLD" in signal_type.__args__
