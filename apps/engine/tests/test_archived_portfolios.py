"""Archived system portfolios: one declarative list, honoured by every reader.

Archived portfolios keep every row they ever wrote (portfolios, trades,
portfolio_performance, portfolio_positions) but stop being treated as active:
they drop off /portfolios, the homepage leaderboard and the comparison chart,
appear under /retired-agents, and are skipped by the price-update bulk
mark-to-market loop so their performance history stays frozen.
"""

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.config import ARCHIVED_PORTFOLIO_OWNER_IDS, is_archived_portfolio
from scripts.update_prices import _fetch_portfolio_owners

RETIRED_OWNER_IDS = {
    "sys-daily-spy-MiniMax-M3",
    "sys-daily-spy-close-MiniMax-M3",
    "sys-daily-spy-deepseek-v4-flash",
    "sys-daily-spy-close-deepseek-v4-flash",
    "sys-daily-tlt-close-deepseek-v4-flash",
    "sys-daily-tlt-close-gpt-5.6-luna",
    "sys-daily-spy-close-jev-local-autoresearched",
    "sys-daily-spy-close-jev-four-regime-champion",
}


def test_archived_owner_ids_declared():
    assert set(ARCHIVED_PORTFOLIO_OWNER_IDS) == RETIRED_OWNER_IDS


def test_is_archived_portfolio_matches_retired_ids():
    for owner_id in RETIRED_OWNER_IDS:
        assert is_archived_portfolio(owner_id) is True, owner_id


@pytest.mark.parametrize(
    "owner_id",
    [
        "sys-pead-drift",
        "sys-max-pain",
        "sys-sentiment-fader",
        "sys-daily-tlt-close-gpt-6-luna",
        "sys-daily-spy-close-MiniMax-M3.1-Flash",
        "sys-daily-spy-close-~typesafe/jev-latest",
        "gpt-6-luna",
        None,
        "",
    ],
)
def test_is_archived_portfolio_leaves_live_ids_active(owner_id):
    assert is_archived_portfolio(owner_id) is False


@pytest.mark.asyncio
async def test_price_update_skips_archived_owners():
    class _Query:
        def select(self, *_args, **_kwargs):
            return self

        def execute(self):
            return SimpleNamespace(
                data=[
                    {"owner_id": "sys-pead-drift"},
                    {"owner_id": "sys-daily-tlt-close-gpt-5.6-luna"},
                    {"owner_id": "gpt-6-luna"},
                ]
            )

    class _Client:
        def table(self, _name):
            return _Query()

    with patch("scripts.update_prices.get_supabase_client", return_value=_Client()):
        owners = await _fetch_portfolio_owners(_Client())

    assert owners == ["sys-pead-drift", "gpt-6-luna"]


REPO_ROOT = Path(__file__).resolve().parents[3]
BOARD_MIGRATION_DIR = REPO_ROOT / "supabase" / "migrations"


def _board_view_excluded_owners() -> set[str]:
    """Owner ids the homepage leaderboard view refuses to rank."""
    candidates = sorted(BOARD_MIGRATION_DIR.glob("*portfolio_leaderboard*.sql"))
    owners: set[str] = set()
    found_in: list[Path] = []
    for path in candidates:
        text = path.read_text()
        start = text.find("excluded(owner_id) AS (")
        if start == -1:
            continue
        # The CTE runs to the next CTE, not to the first "),": every value line
        # ends with "),".
        block = text[start : text.find("bounds AS (", start)]
        ids = set(re.findall(r"\('([^']+)'\)", block))
        if ids:
            owners |= ids
            found_in.append(path)
    assert found_in, "no leaderboard migration declares an archived-owner exclusion"
    return owners


def test_leaderboard_excludes_every_declared_archived_owner():
    """The board reads SQL, the engine reads models.json: they must agree.

    A declared archived portfolio that the view still ranks is the exact defect
    that shipped GPT 5.6 Luna at rank 3 and rank 29 of the same board.
    """
    declared = set(ARCHIVED_PORTFOLIO_OWNER_IDS)
    excluded = _board_view_excluded_owners()

    assert declared - excluded == set(), f"declared archived but still ranked: {sorted(declared - excluded)}"
