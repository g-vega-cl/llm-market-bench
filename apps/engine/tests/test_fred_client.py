"""Tests for the FRED API macroeconomic client and Supabase caching layer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.fred import (
    fetch_fred_series_observations,
    format_fred_observations_markdown,
    get_curated_macro_dashboard,
    resolve_series_alias,
)


def test_resolve_series_alias():
    """Verify alias mapping and raw series pass-through."""
    assert resolve_series_alias("fed_funds") == "FEDFUNDS"
    assert resolve_series_alias("yield_curve_10y2y") == "T10Y2Y"
    assert resolve_series_alias("cpi") == "CPIAUCSL"
    assert resolve_series_alias("WALCL") == "WALCL"
    assert resolve_series_alias("walcl") == "WALCL"
    assert resolve_series_alias("unknown_custom_id") == "UNKNOWN_CUSTOM_ID"


def test_format_fred_observations_markdown():
    """Verify Markdown table generation for observations."""
    obs = [
        {"date": "2026-06-01", "value": 5.33},
        {"date": "2026-07-01", "value": 5.25},
    ]
    md = format_fred_observations_markdown("FEDFUNDS", "Federal Funds Effective Rate", "Percent", "Monthly", obs)
    assert "### 📊 FRED Macro Series: Federal Funds Effective Rate (`FEDFUNDS`)" in md
    assert "2026-07-01" in md
    assert "5.25" in md


@pytest.mark.asyncio
async def test_fetch_fred_series_cache_hit():
    """Verify cache hit from Supabase without making external HTTP requests."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()

    # Cached row within TTL
    mock_res = MagicMock()
    mock_res.data = [
        {
            "series_id": "FEDFUNDS",
            "title": "Federal Funds Effective Rate",
            "units": "Percent",
            "frequency": "Monthly",
            "latest_date": "2026-07-01",
            "latest_value": 5.25,
            "observations": [{"date": "2026-07-01", "value": 5.25}],
            "fetched_at": "2026-08-19T10:00:00Z",
        }
    ]

    mock_eq.execute = AsyncMock(return_value=mock_res)
    mock_select.eq.return_value = mock_eq
    mock_table.select.return_value = mock_select
    mock_sb.table.return_value = mock_table

    with patch("core.fred.get_async_supabase_client", new_callable=AsyncMock) as mock_get_sb:
        mock_get_sb.return_value = mock_sb
        with patch("httpx.AsyncClient.get") as mock_http_get:
            result = await fetch_fred_series_observations("fed_funds", lookback_periods=5)
            assert result["series_id"] == "FEDFUNDS"
            assert result["latest_value"] == 5.25
            assert len(result["observations"]) == 1
            mock_http_get.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_fred_series_cache_miss_and_fetch():
    """Verify external HTTP fetch on cache miss and saving to Supabase."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()

    # Empty cache
    mock_res = MagicMock()
    mock_res.data = []
    mock_eq.execute = AsyncMock(return_value=mock_res)
    mock_select.eq.return_value = mock_eq
    mock_table.select.return_value = mock_select

    mock_upsert = MagicMock()
    mock_upsert.execute = AsyncMock(return_value=MagicMock(data=[{}]))
    mock_table.upsert.return_value = mock_upsert
    mock_sb.table.return_value = mock_table

    mock_http_resp_obs = MagicMock()
    mock_http_resp_obs.status_code = 200
    mock_http_resp_obs.json.return_value = {
        "observations": [
            {"date": "2026-07-01", "value": "5.25"},
            {"date": "2026-06-01", "value": "5.33"},
            {"date": "2026-05-01", "value": "5.33"},
        ]
    }

    mock_http_resp_meta = MagicMock()
    mock_http_resp_meta.status_code = 200
    mock_http_resp_meta.json.return_value = {
        "seriess": [
            {
                "id": "FEDFUNDS",
                "title": "Federal Funds Effective Rate",
                "units": "Percent",
                "frequency": "Monthly",
            }
        ]
    }

    with (
        patch("core.fred.get_async_supabase_client", new_callable=AsyncMock) as mock_get_sb,
        patch("core.fred.FRED_API_KEY", "test_api_key"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get,
    ):
        mock_get_sb.return_value = mock_sb
        mock_http_get.side_effect = [mock_http_resp_meta, mock_http_resp_obs]

        result = await fetch_fred_series_observations("fed_funds", lookback_periods=3)
        assert result["series_id"] == "FEDFUNDS"
        assert result["latest_value"] == 5.25
        assert len(result["observations"]) == 3
        mock_table.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_get_curated_macro_dashboard():
    """Verify aggregated macro dashboard synthesis."""
    with patch("core.fred.fetch_fred_series_observations", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {
            "series_id": "FEDFUNDS",
            "title": "Federal Funds Effective Rate",
            "units": "Percent",
            "frequency": "Monthly",
            "latest_date": "2026-07-01",
            "latest_value": 5.25,
            "observations": [
                {"date": "2026-06-01", "value": 5.33},
                {"date": "2026-07-01", "value": 5.25},
            ],
        }
        dashboard = await get_curated_macro_dashboard(["fed_funds"])
        assert "Macro & Economic Context (FRED)" in dashboard
        assert "Federal Funds Effective Rate" in dashboard
        assert "5.25" in dashboard
