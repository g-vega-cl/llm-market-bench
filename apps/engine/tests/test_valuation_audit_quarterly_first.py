"""Tests verifying the audit_financial_valuation_tool:

1. Requests quarterly metrics first (not annual), letting the FMP provider's
   402→annual fallback handle plan-tier limits.
2. Queries market_barometer_history with the correct column name 'pfcf_ratio'
   (not the wrong 'price_to_fcf_ratio').
3. Does NOT silently swallow exceptions when querying market_barometer_history.
"""


def test_valuation_audit_tool_uses_quarterly_metrics_first():
    """The audit tool must request period='quarter' so high-priority tickers
    (e.g., MU reporting earnings this week) get the most recent metrics.
    The FMP provider's get_key_metrics already falls back to annual on 402."""
    import inspect

    from core.llm import tools as tools_mod

    source = inspect.getsource(tools_mod.execute_financial_valuation_tool)

    # Find the get_key_metrics call and ensure it uses quarterly.
    assert 'period="quarter"' in source, "audit tool not requesting quarterly metrics first"


def test_valuation_audit_tool_uses_correct_pfcf_column_name():
    """The market_barometer_history query must use the actual column 'pfcf_ratio'
    (added in migration 20260621100000), NOT the wrong 'price_to_fcf_ratio'
    which causes a 400 Bad Request from PostgREST."""
    import inspect

    from core.llm import tools as tools_mod

    source = inspect.getsource(tools_mod.execute_financial_valuation_tool)

    # The wrong column name must not appear in the audit tool source.
    assert "price_to_fcf_ratio" not in source, (
        "audit tool queries 'price_to_fcf_ratio' which doesn't exist in DB (column is named 'pfcf_ratio')"
    )
    # The correct column name must appear.
    assert "pfcf_ratio" in source, "audit tool not querying 'pfcf_ratio'"


def test_valuation_audit_tool_logs_barometer_errors():
    """The market_barometer_history query must NOT silently swallow exceptions.
    If PostgREST returns 400 (column drift) or any other error, we should
    log it so the degradation is visible in production."""
    import inspect
    import re

    from core.llm import tools as tools_mod

    source = inspect.getsource(tools_mod.execute_financial_valuation_tool)

    # Find all `except Exception:` blocks in the function and verify none are bare pass.
    pattern = re.compile(r"except Exception:\s*\n\s*pass")
    matches = pattern.findall(source)
    assert len(matches) == 0, (
        f"audit tool has {len(matches)} bare 'except Exception: pass' blocks — should log warning instead"
    )
