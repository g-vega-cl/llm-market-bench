"""Hermetic tests for the live trading-day guard in the sector lane."""

import asyncio


def test_run_sector_trade_skips_thanksgiving(monkeypatch):
    from execution import sector_trading

    def _forbid_db():
        raise AssertionError("database must not be touched on a market holiday")

    monkeypatch.setattr(sector_trading, "get_supabase_client", _forbid_db)

    result = asyncio.run(sector_trading.run_sector_trade(action="entry", target_date_str="2026-11-26"))

    assert result["status"] == "skipped"
    assert "trading day" in result["reason"].lower()


def test_run_sector_trade_skips_weekend(monkeypatch):
    from execution import sector_trading

    def _forbid_db():
        raise AssertionError("database must not be touched on a weekend")

    monkeypatch.setattr(sector_trading, "get_supabase_client", _forbid_db)

    result = asyncio.run(sector_trading.run_sector_trade(action="entry", target_date_str="2026-09-06"))

    assert result["status"] == "skipped"
    assert "trading day" in result["reason"].lower()
