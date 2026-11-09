"""Hermetic unit tests for government fiscal/budget/spending and corporate spending tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.mark.asyncio
async def test_execute_get_government_fiscal_and_spending_tool():
    """Verify get_government_fiscal_and_spending aggregates US & international budgets, deficits, and contracts."""
    from tools.government_tools import execute_get_government_fiscal_and_spending_tool

    mock_liquidity = [
        {
            "record_date": "2026-11-05",
            "tga_balance": 922752000000.0,
            "tot_pub_debt": 40556120784983.65,
            "debt_held_public": 32766722473715.61,
            "intragov_holdings": 7789398311268.04,
            "monthly_deficit_surplus": 257400000000.0,
            "raw_metadata": {
                "tga_deposits": 195747000000.0,
                "tga_withdrawals": 188907000000.0,
                "fytd_deficit_surplus": 1833000000000.0,
                "fytd_receipts": 5192000000000.0,
                "fytd_outlays": 7025000000000.0,
            },
        },
        {
            "record_date": "2026-10-22",
            "tga_balance": 850000000000.0,
            "tot_pub_debt": 40400000000000.0,
            "debt_held_public": 32600000000000.0,
            "intragov_holdings": 7800000000000.0,
            "monthly_deficit_surplus": None,
            "raw_metadata": {},
        },
    ]

    mock_us_budget = [
        {
            "classification_desc": "Social Security",
            "current_fytd_rcpt_outly_amt": 1670000000000.0,
            "prior_fytd_rcpt_outly_amt": 1550000000000.0,
            "current_month_rcpt_outly_amt": 141000000000.0,
        },
        {
            "classification_desc": "National Defense",
            "current_fytd_rcpt_outly_amt": 965200000000.0,
            "prior_fytd_rcpt_outly_amt": 890000000000.0,
            "current_month_rcpt_outly_amt": 88400000000.0,
        },
        {
            "classification_desc": "Net Interest",
            "current_fytd_rcpt_outly_amt": 1054000000000.0,
            "prior_fytd_rcpt_outly_amt": 950000000000.0,
            "current_month_rcpt_outly_amt": 76800000000.0,
        },
    ]

    mock_us_agencies = [
        {
            "agency_name": "Department of Defense",
            "budget_authority_amount": 2616500000000.0,
            "obligated_amount": 1350700000000.0,
            "outlay_amount": 1364000000000.0,
        }
    ]

    mock_ca_budget = [
        {
            "fiscal_year": "2025/2026",
            "ministry": "National Defence",
            "curr_cad": 49540000000.0,
            "prev_cad": 35040000000.0,
            "yoy_pct": 41.38,
        }
    ]

    mock_global_spending = {
        "defense": [
            {"country": "Germany", "code": "DEU", "year": "2024", "val_usd": 113600000000.0, "yoy_pct": 31.83},
            {"country": "United States", "code": "USA", "year": "2024", "val_usd": 954400000000.0, "yoy_pct": 4.91},
        ],
        "infrastructure_gcf": [
            {"country": "United Kingdom", "code": "GBR", "year": "2024", "val_usd": 420000000000.0, "yoy_pct": 11.25},
        ],
        "eurostat_fiscal": [
            {"geo": "DE", "period": "2024", "deficit_pct_gdp": -2.9, "debt_pct_gdp": 62.8},
            {"geo": "FR", "period": "2024", "deficit_pct_gdp": -5.1, "debt_pct_gdp": 115.7},
        ],
    }

    mock_contracts = [
        {
            "country": "US",
            "award_id": "W56JSR26F0041",
            "recipient_name": "PALANTIR USG INC",
            "award_amount": 637653890.26,
            "currency": "USD",
            "agency_name": "Department of Defense",
            "award_date": "2026-10-30",
            "description": "CDAO Maven Smart System",
        }
    ]

    with (
        patch("tools.government_tools._get_liquidity_records", new_callable=AsyncMock, return_value=mock_liquidity),
        patch(
            "tools.government_tools._fetch_us_budget_categories", new_callable=AsyncMock, return_value=mock_us_budget
        ),
        patch("tools.government_tools._fetch_us_agency_budgets", new_callable=AsyncMock, return_value=mock_us_agencies),
        patch(
            "tools.government_tools._fetch_canada_ministry_budgets",
            new_callable=AsyncMock,
            return_value=mock_ca_budget,
        ),
        patch(
            "tools.government_tools._fetch_global_sovereign_spending",
            new_callable=AsyncMock,
            return_value=mock_global_spending,
        ),
        patch("tools.government_tools._get_contract_deals", new_callable=AsyncMock, return_value=mock_contracts),
        patch(
            "tools.government_tools._fetch_fed_liquidity_snapshot",
            new_callable=AsyncMock,
            return_value={"avg_rates": {"Treasury Bills": 4.01, "Treasury Notes": 3.40}},
        ),
    ):
        report = await execute_get_government_fiscal_and_spending_tool(country="ALL", ticker="PLTR", limit=5)

    assert "922.75B" in report or "922.8B" in report
    assert "40.56T" in report
    assert "National Defense" in report
    assert "National Defence" in report
    assert "+41.4%" in report
    assert "Germany" in report
    assert "+31.8%" in report
    assert "PALANTIR USG INC" in report
    assert "637.65M" in report or "637.7M" in report
    assert "Treasury Bills: 4.01%" in report


@pytest.mark.asyncio
async def test_government_tools_inner_fetchers():
    """Verify inner HTTP & DB fetchers in tools.government_tools with mocked httpx/Supabase."""
    from tools.government_tools import (
        _fetch_canada_ministry_budgets,
        _fetch_fed_liquidity_snapshot,
        _fetch_global_sovereign_spending,
        _fetch_us_agency_budgets,
        _fetch_us_budget_categories,
        _get_contract_deals,
        _get_liquidity_records,
    )

    # 1. _get_liquidity_records via Supabase
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = (
        MagicMock(data=[{"record_date": "2026-11-05", "tga_balance": 922752.0}])
    )
    with patch("tools.government_tools.get_supabase_client", return_value=mock_sb):
        liq = await _get_liquidity_records(limit=5)
    assert liq[0]["tga_balance"] == 922752.0 * 1_000_000.0

    # 2. _fetch_us_budget_categories & _fetch_us_agency_budgets
    mock_mts9_resp = MagicMock(status_code=200)
    mock_mts9_resp.json.return_value = {
        "data": [
            {
                "classification_desc": "National Defense",
                "record_date": "2026-09-30",
                "current_month_rcpt_outly_amt": "88400000000",
                "current_fytd_rcpt_outly_amt": "965200000000",
                "prior_fytd_rcpt_outly_amt": "890000000000",
            }
        ]
    }
    mock_ag_resp = MagicMock(status_code=200)
    mock_ag_resp.json.return_value = {
        "results": [{"agency_name": "Department of Defense", "budget_authority_amount": 2616500000000.0}]
    }
    mock_ca_resp = MagicMock(status_code=200)
    mock_ca_resp.text = (
        "Fscl-yr_Ex-fin,Min-portfolio_Portefeuille-min-eng,Auth-type_Type-aut,"
        "Net-exp-curr-yr_Dep-nettes-ex-en-cours,Net-exp-prev-yr_Dep-nettes-ex-prec\n"
        "2025/2026,National Defence,Budgetary-Budgétaire,49540000,35040000\n"
    )
    mock_wb_resp = MagicMock(status_code=200)
    mock_wb_resp.json.return_value = [
        {"page": 1},
        [
            {"countryiso3code": "DEU", "country": {"value": "Germany"}, "date": "2024", "value": 113600000000.0},
            {"countryiso3code": "DEU", "country": {"value": "Germany"}, "date": "2023", "value": 86170000000.0},
        ],
    ]
    mock_eu_resp = MagicMock(status_code=200)
    mock_eu_resp.json.return_value = {
        "value": {"0": -2.9, "1": 62.8},
        "dimension": {
            "geo": {"category": {"index": {"DE": 0}}},
            "na_item": {"category": {"index": {"B9": 0, "GD": 1}}},
            "time": {"category": {"index": {"2024": 0}}},
        },
    }
    mock_rates_resp = MagicMock(status_code=200)
    mock_rates_resp.json.return_value = {
        "data": [{"security_desc": "Treasury Bills", "avg_interest_rate_amt": "4.014"}]
    }

    mock_client = AsyncMock()
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_client.get = AsyncMock(return_value=mock_mts9_resp)
        cats = await _fetch_us_budget_categories()
        assert len(cats) == 1 and cats[0]["classification_desc"] == "National Defense"

        mock_client.get = AsyncMock(return_value=mock_ag_resp)
        ags = await _fetch_us_agency_budgets()
        assert len(ags) == 1 and ags[0]["agency_name"] == "Department of Defense"

        mock_client.get = AsyncMock(return_value=mock_ca_resp)
        ca_min = await _fetch_canada_ministry_budgets()
        assert len(ca_min) == 1 and ca_min[0]["ministry"] == "National Defence"
        assert ca_min[0]["yoy_pct"] > 41.0

        mock_client.get = AsyncMock(side_effect=[mock_wb_resp, mock_wb_resp, mock_eu_resp])
        glob = await _fetch_global_sovereign_spending()
        assert glob["defense"][0]["code"] == "DEU"
        assert glob["eurostat_fiscal"][0]["geo"] == "DE"

        mock_client.get = AsyncMock(return_value=mock_rates_resp)
        with patch(
            "core.fred.fetch_fred_series_observations",
            new_callable=AsyncMock,
            return_value={"latest_value": 21500.0},
        ):
            snap = await _fetch_fed_liquidity_snapshot()
        assert snap["avg_rates"]["Treasury Bills"] == 4.014

    # 3. _get_contract_deals fallback to live fetchers
    with (
        patch("tools.government_tools.get_supabase_client", side_effect=RuntimeError("No DB")),
        patch(
            "tools.government_tools.fetch_usaspending_contracts",
            new_callable=AsyncMock,
            return_value=[{"award_id": "A1", "award_amount": 1000.0, "country": "US", "recipient_name": "PLTR"}],
        ),
        patch(
            "tools.government_tools.fetch_canadabuys_contracts",
            new_callable=AsyncMock,
            return_value=[{"award_id": "CA1", "award_amount": 500.0, "country": "CA", "recipient_name": "CAE"}],
        ),
    ):
        deals = await _get_contract_deals(country="ALL", query=None, limit=5)
    assert len(deals) == 2 and deals[0]["award_id"] == "A1"


@pytest.mark.asyncio
async def test_execute_get_corporate_spending_tool_single_ticker():
    """Verify single-ticker corporate spending breakdown (CapEx, R&D, Buybacks, M&A, Gov Contracts)."""
    from tools.corporate_spending_tools import execute_get_corporate_spending_tool

    mock_cf = [
        {
            "date": "2026-09-30",
            "period": "Q1",
            "fiscalYear": "2027",
            "capitalExpenditure": -25902000000.0,
            "operatingCashFlow": 49483000000.0,
            "freeCashFlow": 23581000000.0,
            "commonStockRepurchased": -9956000000.0,
            "commonDividendsPaid": -6800000000.0,
            "acquisitionsNet": -450000000.0,
        },
        {
            "date": "2025-09-30",
            "period": "Q1",
            "fiscalYear": "2026",
            "capitalExpenditure": -14923000000.0,
            "operatingCashFlow": 34180000000.0,
            "freeCashFlow": 19257000000.0,
            "commonStockRepurchased": -4100000000.0,
            "commonDividendsPaid": -5500000000.0,
            "acquisitionsNet": 0.0,
        },
    ]

    mock_inc = [
        {
            "date": "2026-09-30",
            "period": "Q1",
            "fiscalYear": "2027",
            "revenue": 81327000000.0,
            "researchAndDevelopmentExpenses": 9381000000.0,
            "sellingGeneralAndAdministrativeExpenses": 7800000000.0,
            "operatingIncome": 38000000000.0,
        },
        {
            "date": "2025-09-30",
            "period": "Q1",
            "fiscalYear": "2026",
            "revenue": 65585000000.0,
            "researchAndDevelopmentExpenses": 7544000000.0,
            "sellingGeneralAndAdministrativeExpenses": 6900000000.0,
            "operatingIncome": 30500000000.0,
        },
    ]

    mock_metrics = [
        {
            "date": "2026-06-30",
            "returnOnInvestedCapital": 0.3005,
            "capexToOperatingCashFlow": 0.4832,
            "capexToRevenue": 0.2323,
            "researchAndDevelopementToRevenue": 0.1149,
        }
    ]

    mock_ma = [
        {
            "symbol": "MSFT",
            "companyName": "Microsoft Corp",
            "targetedCompanyName": "AI Cloud Robotics Inc",
            "transactionDate": "2026-08-15",
        }
    ]

    mock_contracts = [
        {
            "country": "US",
            "award_id": "DOD-MSFT-01",
            "recipient_name": "MICROSOFT CORPORATION",
            "award_amount": 220000000.0,
            "currency": "USD",
            "agency_name": "Department of Defense",
            "award_date": "2026-10-12",
            "description": "Azure DoD Cloud Infrastructure",
        }
    ]

    with (
        patch(
            "tools.corporate_spending_tools._fetch_ticker_spending_statements",
            new_callable=AsyncMock,
            return_value=(mock_cf, mock_inc, mock_metrics),
        ),
        patch(
            "tools.corporate_spending_tools._fetch_recent_ma_deals",
            new_callable=AsyncMock,
            return_value=mock_ma,
        ),
        patch(
            "tools.corporate_spending_tools._fetch_company_gov_contracts",
            new_callable=AsyncMock,
            return_value=mock_contracts,
        ),
    ):
        report = await execute_get_corporate_spending_tool(ticker="MSFT", period="quarter", limit=2)

    assert "MSFT" in report
    assert "25.90B" in report or "25.9B" in report
    assert "9.38B" in report or "9.4B" in report
    assert "9.96B" in report or "10.0B" in report
    assert "MICROSOFT CORPORATION" in report
    assert "AI Cloud Robotics Inc" in report


@pytest.mark.asyncio
async def test_corporate_spending_inner_fmp_fetchers():
    """Verify FMP HTTP fetchers in corporate_spending_tools with mocked httpx."""
    from tools.corporate_spending_tools import (
        _fetch_recent_ma_deals,
        _fetch_ticker_spending_statements,
    )

    cf_resp = httpx.Response(200, json=[{"date": "2026-09-30", "capitalExpenditure": -100.0}])
    inc_resp = httpx.Response(200, json=[{"date": "2026-09-30", "revenue": 500.0}])
    km_resp = httpx.Response(200, json=[{"date": "2026-09-30", "returnOnInvestedCapital": 0.25}])
    ma_resp = httpx.Response(
        200,
        json=[{"symbol": "MSFT", "companyName": "Microsoft", "targetedCompanyName": "TargetCo"}],
    )

    mock_client = AsyncMock()
    with (
        patch("tools.corporate_spending_tools.FMP_API_KEY", "test-key"),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=[cf_resp, inc_resp, km_resp])
        cf, inc, km = await _fetch_ticker_spending_statements("MSFT", period="quarter", limit=2)
        assert len(cf) == 1 and len(inc) == 1 and len(km) == 1

        mock_client.get = AsyncMock(return_value=ma_resp)
        deals = await _fetch_recent_ma_deals("MSFT", limit=5)
        assert len(deals) == 1 and deals[0]["symbol"] == "MSFT"


@pytest.mark.asyncio
async def test_execute_get_corporate_spending_tool_basket():
    """Verify multi-ticker CapEx and R&D comparison basket when ticker is omitted."""
    from tools.corporate_spending_tools import execute_get_corporate_spending_tool

    async def fake_fetch(ticker: str, period: str = "quarter", limit: int = 4):
        return (
            [
                {
                    "date": "2026-09-30",
                    "period": "Q3",
                    "capitalExpenditure": -25000000000.0 if ticker == "MSFT" else -15000000000.0,
                    "operatingCashFlow": 50000000000.0,
                    "freeCashFlow": 25000000000.0,
                    "commonStockRepurchased": -5000000000.0,
                    "acquisitionsNet": 0.0,
                },
                {
                    "date": "2025-09-30",
                    "period": "Q3",
                    "capitalExpenditure": -15000000000.0 if ticker == "MSFT" else -12000000000.0,
                    "operatingCashFlow": 40000000000.0,
                    "freeCashFlow": 25000000000.0,
                    "commonStockRepurchased": -4000000000.0,
                    "acquisitionsNet": 0.0,
                },
            ],
            [
                {
                    "date": "2026-09-30",
                    "period": "Q3",
                    "revenue": 80000000000.0,
                    "researchAndDevelopmentExpenses": 10000000000.0,
                    "sellingGeneralAndAdministrativeExpenses": 7000000000.0,
                }
            ],
            [{"returnOnInvestedCapital": 0.28}],
        )

    with patch("tools.corporate_spending_tools._fetch_ticker_spending_statements", side_effect=fake_fetch):
        report = await execute_get_corporate_spending_tool(tickers=["MSFT", "GOOGL"], period="quarter")

    assert "MSFT" in report
    assert "GOOGL" in report
    assert "+66.7%" in report


def test_format_key_metric_period_includes_reinvestment_ratios():
    """Verify _format_key_metric_period surfaces CapEx/Rev, CapEx/OCF, R&D/Rev, and ROIC."""
    from tools.valuation import _format_key_metric_period

    entry = {
        "date": "2026-06-30",
        "period": "FY",
        "calendarYear": "2026",
        "peRatio": 30.5,
        "roe": 0.35,
        "returnOnInvestedCapital": 0.3005,
        "capexToOperatingCashFlow": 0.4832,
        "capexToRevenue": 0.2323,
        "researchAndDevelopementToRevenue": 0.1149,
    }
    formatted = _format_key_metric_period(1, entry)
    assert "ROIC: 30.05%" in formatted
    assert "CapEx/Operating Cash Flow: 48.32%" in formatted
    assert "CapEx/Revenue: 23.23%" in formatted
    assert "R&D/Revenue: 11.49%" in formatted
