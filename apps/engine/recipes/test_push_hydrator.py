"""Tests for news excerpt building in push_hydrator."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from recipes.push_hydrator import build_news_excerpt, hydrate_stage_prompt
from recipes.push_schema import NewsBlock, StrategyStage


def test_excerpt_centers_on_keyword_hit():
    text = ("alpha " * 100) + "Trump announced new chips tariffs " + ("omega " * 100)
    out = build_news_excerpt(text, ["chips"])
    assert "chips" in out
    assert out.startswith("…") and out.endswith("…")
    assert len(out) < 400


def test_excerpt_case_insensitive_and_whitespace_collapsed():
    out = build_news_excerpt("Line one\n\n  mentions   TRUMP here", ["trump"])
    assert out == "Line one mentions TRUMP here"


def test_excerpt_falls_back_to_lead_when_no_keywords():
    text = "word " * 200
    out = build_news_excerpt(text, [])
    assert out.endswith("…")
    assert len(out) <= 302


def test_excerpt_falls_back_to_lead_when_no_body_hit():
    text = "start " + ("filler " * 200)
    out = build_news_excerpt(text, ["nvidia"])
    assert out.startswith("start")
    assert out.endswith("…")


def test_excerpt_empty_text():
    assert build_news_excerpt("", ["x"]) == ""
    assert build_news_excerpt(None, ["x"]) == ""


def test_hydrate_includes_excerpt_line():
    as_of = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
    rows = [
        {
            "title": "Nvidia Board Vote",
            "full_text": "Intro text. Trump said chips exports will change.",
            "date_published": "2026-11-12T01:05:00+00:00",
            "tickers": ["NVDA"],
        }
    ]
    stage = StrategyStage(id="s1", blocks=[NewsBlock(type="news", id="n1", contains=["chips"], recency_hours=48)])
    out = hydrate_stage_prompt(stage, rows, [], as_of)
    assert "Nvidia Board Vote (Tickers: NVDA)" in out
    assert "\n  Intro text. Trump said chips exports will change." in out


def test_excerpt_end_trim_boundary_exact():
    # Space lands exactly at index pos+EXCERPT_RADIUS; must back up to the prior space.
    text = "KEY!" + " w" * 200
    assert build_news_excerpt(text, ["key"]) == "KEY!" + " w" * 72 + "…"


_CASES_PATH = Path(__file__).resolve().parents[3] / "packages" / "config" / "news-excerpt-cases.json"
_CASES = json.loads(_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_excerpt_matches_shared_fixture(case):
    # Same cases are asserted by apps/web/src/features/recipes/news-excerpt.test.ts.
    assert build_news_excerpt(case["text"], case["keywords"]) == case["expected"]
