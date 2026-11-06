"""Tests for vetted, deduplicated intraday news persistence."""

from unittest.mock import MagicMock

import pytest

from trading.intraday_news_store import persist_intraday_news


def _item(headline, h, source="Alpaca Benzinga"):
    return {
        "headline": headline,
        "summary": "s",
        "source": source,
        "url": "https://x/1",
        "tickers": ["SPY"],
        "published_at": "2026-11-06T18:00:00Z",
        "source_id_hash": h,
    }


def _sb(existing_hashes=(), recent_headlines=()):
    sb = MagicMock()
    table = MagicMock()
    sb.table.return_value = table
    # hash existence lookup
    table.select.return_value.in_.return_value.execute.return_value.data = [
        {"source_id_hash": h} for h in existing_hashes
    ]
    # recent headline lookup
    table.select.return_value.gte.return_value.limit.return_value.execute.return_value.data = [
        {"headline": t} for t in recent_headlines
    ]
    return sb, table


def _evaluator(choice_by_headline):
    async def _eval(event):
        choice, conf = choice_by_headline.get(event["headline"], ("NOISE", 90.0))
        return {
            "choice": choice,
            "confidence": conf,
            "is_market_moving": choice == "MARKET_MOVING" and conf >= 70.0,
        }

    return _eval


@pytest.mark.asyncio
async def test_persists_both_market_moving_and_noise_items_with_real_confidence():
    sb, table = _sb()
    items = [
        _item("Fed cuts rates by 50bp", "h1"),
        _item("Routine PR blurb", "h2"),
        _item("Failed evaluation error", "h3"),
    ]
    ev = _evaluator(
        {
            "Fed cuts rates by 50bp": ("MARKET_MOVING", 88.5),
            "Routine PR blurb": ("NOISE", 91.0),
            "Failed evaluation error": ("NOISE", 0.0),
        }
    )

    count = await persist_intraday_news(items, sb_client=sb, evaluate=ev)

    assert count == 2
    rows = table.upsert.call_args[0][0]
    assert [r["source_id_hash"] for r in rows] == ["h1", "h2"]
    assert rows[0]["jev_confidence"] == 88.5
    assert rows[0]["jev_choice"] == "MARKET_MOVING"
    assert rows[1]["jev_confidence"] == 91.0
    assert rows[1]["jev_choice"] == "NOISE"
    assert table.upsert.call_args[1]["on_conflict"] == "source_id_hash"


@pytest.mark.asyncio
async def test_skips_already_stored_hashes_without_calling_evaluator():
    sb, table = _sb(existing_hashes=["h1"])
    calls = []

    async def ev(event):
        calls.append(event)
        return {"choice": "MARKET_MOVING", "confidence": 90.0, "is_market_moving": True}

    count = await persist_intraday_news([_item("Fed cuts rates", "h1")], sb_client=sb, evaluate=ev)

    assert count == 0
    assert calls == []
    table.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_drops_cross_source_duplicate_of_recent_headline():
    sb, table = _sb(recent_headlines=["White House weighs executive order labeling nonprofits terrorist"])
    ev = _evaluator({"White House Weighs Executive Order Labeling Some Nonprofits Terrorist": ("MARKET_MOVING", 80.0)})
    items = [_item("White House Weighs Executive Order Labeling Some Nonprofits Terrorist", "h9", "Polygon Wire")]

    count = await persist_intraday_news(items, sb_client=sb, evaluate=ev)

    assert count == 0
    table.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_empty_input_returns_zero():
    assert await persist_intraday_news([], sb_client=MagicMock()) == 0


@pytest.mark.asyncio
async def test_kill_switch_stores_unvetted_without_calling_jev(monkeypatch):
    monkeypatch.setenv("INTRADAY_NEWS_JEV_VETTING", "false")
    sb, table = _sb()
    calls = []

    async def ev(event):
        calls.append(event)
        return {"choice": "MARKET_MOVING", "confidence": 90.0, "is_market_moving": True}

    count = await persist_intraday_news([_item("Fed cuts rates", "h1")], sb_client=sb, evaluate=ev)

    assert count == 1
    assert calls == []
    row = table.upsert.call_args[0][0][0]
    assert row["jev_choice"] == "UNVETTED"
    assert row["jev_confidence"] == 0.0
