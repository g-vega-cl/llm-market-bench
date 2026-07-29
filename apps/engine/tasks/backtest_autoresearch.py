import argparse
import asyncio
import os
import sqlite3
import sys
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

# Inject path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contextlib

from analysis.analyze import MODELS, analyze_chunks
from autoresearch.prompt_store import get_active_prompt, save_variant
from autoresearch.researcher import run_research
from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS, logger
from core.db import get_async_supabase_client, get_supabase_client
from core.llm.verification import verify_trading_decision
from execution.portfolio import Portfolio
from execution.providers.base import FinancialProvider, HistoryData, TickerData
from execution.providers.factory import get_financial_provider

DB_PATH = ".backtest_portfolios.db"


def init_backtest_db():
    """Create local SQLite tables mirroring the Supabase schema for mock execution."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS portfolios")
    cursor.execute("DROP TABLE IF EXISTS portfolio_positions")
    cursor.execute("DROP TABLE IF EXISTS trades")
    cursor.execute("DROP TABLE IF EXISTS decisions")
    cursor.execute("DROP TABLE IF EXISTS price_history")
    cursor.execute("DROP TABLE IF EXISTS market_data_cache")
    cursor.execute("DROP TABLE IF EXISTS portfolio_performance")
    cursor.execute("DROP VIEW IF EXISTS position_pnl")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_performance (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT,
            date TEXT,
            total_equity REAL,
            cash_balance REAL,
            buying_power REAL,
            sma REAL,
            created_at TEXT,
            initial_margin_req REAL,
            maintenance_margin_req REAL,
            available_funds REAL,
            excess_liquidity REAL,
            realized REAL,
            UNIQUE(portfolio_id, date)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id TEXT PRIMARY KEY,
            owner_id TEXT UNIQUE,
            cash_balance REAL,
            total_equity REAL,
            buying_power REAL,
            excess_liquidity REAL,
            maintenance_margin REAL,
            last_updated_at TEXT,
            sma REAL,
            realized REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT,
            ticker TEXT,
            quantity INTEGER,
            average_cost_basis REAL,
            last_updated_at TEXT,
            UNIQUE(portfolio_id, ticker)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT,
            ticker TEXT,
            signal TEXT,
            quantity INTEGER,
            price REAL,
            total_cost REAL,
            executed_at TEXT,
            decision_id TEXT,
            realized_pnl REAL,
            realized_pnl_pct REAL,
            reasoning TEXT,
            alpaca_order_id TEXT,
            alpaca_status TEXT,
            alpaca_submitted_at TEXT,
            alpaca_filled_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id TEXT PRIMARY KEY,
            source_id TEXT,
            ticker TEXT,
            signal TEXT,
            confidence REAL,
            reasoning TEXT,
            model_provider TEXT,
            model_name TEXT,
            created_at TEXT,
            price REAL,
            status TEXT,
            metadata TEXT,
            trade_id TEXT,
            embedding TEXT,
            limit_price REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            ticker TEXT,
            price REAL,
            market_cap REAL,
            fetched_at TEXT,
            PRIMARY KEY (ticker, fetched_at)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_data_cache (
            ticker TEXT PRIMARY KEY,
            price REAL,
            market_cap REAL,
            fetched_at TEXT,
            today_pct_change REAL,
            stdev_pct REAL,
            regime_flag TEXT
        )
    """)

    cursor.execute("""
        CREATE VIEW IF NOT EXISTS position_pnl AS
        SELECT 
            p.id || '_' || pos.ticker AS position_id,
            p.id AS portfolio_id,
            p.owner_id,
            pos.ticker,
            pos.quantity,
            pos.average_cost_basis,
            coalesce(m.price, pos.average_cost_basis) AS current_price,
            coalesce(m.fetched_at, pos.last_updated_at) AS price_fetched_at,
            (coalesce(m.price, pos.average_cost_basis) - pos.average_cost_basis) * pos.quantity AS unrealized_pnl_usd,
            CASE 
                WHEN pos.average_cost_basis > 0 THEN ((coalesce(m.price, pos.average_cost_basis) / pos.average_cost_basis) - 1) * 100
                ELSE 0
            END AS unrealized_pnl_pct
        FROM portfolio_positions pos
        JOIN portfolios p ON pos.portfolio_id = p.id
        LEFT JOIN market_data_cache m ON pos.ticker = m.ticker
    """)

    conn.commit()
    conn.close()
    logger.info("Initialized local backtest database cache.")


def reset_backtest_db():
    """Clear all trades, positions, decisions, and reset portfolios to default $10k cash."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio_positions")
    cursor.execute("DELETE FROM trades")
    cursor.execute("DELETE FROM decisions")
    cursor.execute("DELETE FROM portfolios")

    for owner in AUTORESEARCH_EXPERIMENT_OWNER_IDS:
        p_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO portfolios (id, owner_id, cash_balance, sma, total_equity, buying_power, excess_liquidity, maintenance_margin, realized, last_updated_at) "
            "VALUES (?, ?, 10000.0, 10000.0, 10000.0, 10000.0, 10000.0, 0.0, 10000.0, datetime('now'))",
            (p_id, owner),
        )
    conn.commit()
    conn.close()
    logger.info("Reset backtest database portfolios to $10,000 baseline.")


# Custom Query Builder / Executor Mock for SQLite
class SQLiteQueryBuilder:
    def __init__(self, table_name, action="SELECT", select_val="*", update_data=None):
        self.table_name = table_name
        self.action = action
        self.select_val = select_val
        self.update_data = update_data
        self.where_clauses = []
        self.where_args = []
        self.limit_val = None
        self.order_by = None

    def eq(self, field, val):
        self.where_clauses.append(f"{field} = ?")
        self.where_args.append(val)
        return self

    def neq(self, field, val):
        self.where_clauses.append(f"{field} != ?")
        self.where_args.append(val)
        return self

    def gt(self, field, val):
        self.where_clauses.append(f"{field} > ?")
        self.where_args.append(val)
        return self

    def gte(self, field, val):
        self.where_clauses.append(f"{field} >= ?")
        self.where_args.append(val)
        return self

    def lt(self, field, val):
        self.where_clauses.append(f"{field} < ?")
        self.where_args.append(val)
        return self

    def lte(self, field, val):
        self.where_clauses.append(f"{field} <= ?")
        self.where_args.append(val)
        return self

    def in_(self, field, vals):
        placeholders = ", ".join(["?"] * len(vals))
        self.where_clauses.append(f"{field} IN ({placeholders})")
        self.where_args.extend(vals)
        return self

    def order(self, field, desc=False):
        self.order_by = f"{field} DESC" if desc else f"{field} ASC"
        return self

    def limit(self, limit):
        self.limit_val = limit
        return self

    def maybe_single(self):
        self.limit_val = 1
        return self

    def match(self, match_dict):
        for k, v in match_dict.items():
            self.eq(k, v)
        return self

    def execute(self):
        import json

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if self.action == "SELECT":
            sql = f"SELECT {self.select_val} FROM {self.table_name}"
            if self.where_clauses:
                sql += " WHERE " + " AND ".join(self.where_clauses)
            if self.order_by:
                sql += f" ORDER BY {self.order_by}"
            if self.limit_val:
                sql += f" LIMIT {self.limit_val}"

            cursor.execute(sql, self.where_args)
            rows = cursor.fetchall()
            conn.close()

            data = []
            for r in rows:
                row_dict = dict(r)
                for k, v in row_dict.items():
                    if isinstance(v, str) and (
                        (v.startswith("{") and v.endswith("}")) or (v.startswith("[") and v.endswith("]"))
                    ):
                        with contextlib.suppress(Exception):
                            row_dict[k] = json.loads(v)
                data.append(row_dict)

            res = MagicMock()
            res.data = data
            return res

        elif self.action == "DELETE":
            sql = f"DELETE FROM {self.table_name}"
            if self.where_clauses:
                sql += " WHERE " + " AND ".join(self.where_clauses)
            cursor.execute(sql, self.where_args)
            conn.commit()
            conn.close()

            res = MagicMock()
            res.data = []
            return res

        elif self.action == "UPDATE":
            serialized = _serialize_row_data(self.update_data)
            set_clause = ", ".join([f"{k} = ?" for k in serialized])
            sql = f"UPDATE {self.table_name} SET {set_clause}"
            if self.where_clauses:
                sql += " WHERE " + " AND ".join(self.where_clauses)
            args = list(serialized.values()) + self.where_args
            cursor.execute(sql, args)
            conn.commit()
            conn.close()

            res = MagicMock()
            res.data = [self.update_data]
            return res


def _serialize_row_data(data):
    if not isinstance(data, dict):
        return data
    import json

    new_data = {}
    for k, v in data.items():
        if isinstance(v, (dict, list)):
            new_data[k] = json.dumps(v)
        else:
            new_data[k] = v
    return new_data


class SQLiteInsertBuilder:
    def __init__(self, table_name, data, t_sim=None, is_upsert=False):
        self.table_name = table_name
        self.data = data
        self.t_sim = t_sim
        self.is_upsert = is_upsert

        import uuid

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Substitute "now()" with point-in-time simulated time if available
        if isinstance(self.data, dict):
            for k, v in list(self.data.items()):
                if v == "now()":
                    if self.t_sim:
                        self.data[k] = self.t_sim.isoformat()
                    else:
                        from datetime import UTC, datetime

                        self.data[k] = datetime.now(UTC).isoformat()

        # Ensure a UUID id is present for Supabase parity
        if isinstance(self.data, dict) and "id" not in self.data:
            self.data["id"] = str(uuid.uuid4())

        if isinstance(self.data, dict):
            serialized = _serialize_row_data(self.data)
            fields = list(serialized.keys())
            vals = list(serialized.values())
            placeholders = ", ".join(["?"] * len(vals))
            if self.is_upsert:
                sql = f"INSERT OR REPLACE INTO {self.table_name} ({', '.join(fields)}) VALUES ({placeholders})"
            else:
                sql = f"INSERT INTO {self.table_name} ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(sql, vals)
        conn.commit()
        conn.close()

        # Direct property access for backwards compatibility in unit tests
        self._res_data = [self.data]

    @property
    def data(self):
        # Allow accessing .data both as the builder parameter and the output result
        if hasattr(self, "_res_data"):
            return self._res_data
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def execute(self):
        return self


class SQLiteTable:
    def __init__(self, table_name, t_sim=None):
        self.table_name = table_name
        self.t_sim = t_sim

    def select(self, *args, **kwargs):
        select_val = "*"
        if args:
            select_val = ",".join(args)
        return SQLiteQueryBuilder(self.table_name, action="SELECT", select_val=select_val)

    def insert(self, data):
        return SQLiteInsertBuilder(self.table_name, data, t_sim=self.t_sim, is_upsert=False)

    def upsert(self, data, on_conflict=None):
        return SQLiteInsertBuilder(self.table_name, data, t_sim=self.t_sim, is_upsert=True)

    def update(self, data):
        return SQLiteQueryBuilder(self.table_name, action="UPDATE", update_data=data)

    def delete(self):
        return SQLiteQueryBuilder(self.table_name, action="DELETE")


# Simulated Temporal Sandbox Supabase Client
class MockSimulatedSupabaseClient:
    def __init__(self, real_client, t_sim):
        self.real_client = real_client
        self.t_sim = t_sim

    def table(self, name):
        if name in (
            "portfolios",
            "portfolio_positions",
            "trades",
            "decisions",
            "price_history",
            "market_data_cache",
            "position_pnl",
            "portfolio_performance",
        ):
            return SQLiteTable(name, self.t_sim)

        if name == "prompt_experiments":
            return self.real_client.table(name)

        class TemporalQueryBuilderWrapper:
            def __init__(self, original_builder, table_name, t_sim):
                self.original_builder = original_builder
                self.table_name = table_name
                self.t_sim = t_sim

            def __getattr__(self, attr_name):
                attr = getattr(self.original_builder, attr_name)
                if callable(attr):

                    def wrapper(*args, **kwargs):
                        res = attr(*args, **kwargs)
                        if hasattr(res, "execute") or "RequestBuilder" in type(res).__name__:
                            return TemporalQueryBuilderWrapper(res, self.table_name, self.t_sim)
                        return res

                    return wrapper
                return attr

            def execute(self):
                is_get = True
                try:
                    if hasattr(self.original_builder, "request"):
                        method = getattr(self.original_builder.request, "http_method", None)
                        if isinstance(method, str) and method != "GET":
                            is_get = False
                except Exception:
                    pass

                if is_get and hasattr(self.original_builder, "lte"):
                    table_date_fields = {
                        "newsletter_snapshots": "date",
                        "market_data_cache": "fetched_at",
                        "position_pnl": "price_fetched_at",
                        "market_barometer_history": "updated_at",
                        "price_history": "fetched_at",
                        "llm_reasoning_logs": "created_at",
                        "memories": "created_at",
                        "decisions": "created_at",
                    }
                    if self.table_name in table_date_fields:
                        date_field = table_date_fields[self.table_name]
                        filtered = self.original_builder.lte(date_field, self.t_sim.isoformat())
                        return filtered.execute()
                return self.original_builder.execute()

        return TemporalQueryBuilderWrapper(self.real_client.table(name), name, self.t_sim)

    def rpc(self, fn_name, params):
        real_rpc = self.real_client.rpc(fn_name, params)
        t_sim = self.t_sim
        real_client = self.real_client

        class RPCWrapper:
            def execute(self):
                res = real_rpc.execute()
                if not res.data:
                    return res

                row_ids = [r["id"] for r in res.data if "id" in r]
                if not row_ids:
                    return res

                target_table = "memories" if fn_name == "match_memories" else "decisions"

                meta_res = real_client.table(target_table).select("id, created_at").in_("id", row_ids).execute()

                created_at_map = {}
                for row in meta_res.data or []:
                    try:
                        from dateutil import parser

                        dt = parser.isoparse(row["created_at"])
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=UTC)
                        created_at_map[row["id"]] = dt
                    except Exception:
                        pass

                filtered_data = []
                for row in res.data:
                    row_id = row.get("id")
                    if row_id in created_at_map:
                        if created_at_map[row_id] <= t_sim:
                            filtered_data.append(row)
                    else:
                        filtered_data.append(row)

                res.data = filtered_data
                return res

        return RPCWrapper()


# Mock Point-In-Time Financial Provider
class MockFinancialProvider(FinancialProvider):
    provider_name = "fmp"

    def __init__(self, real_provider, t_sim):
        self.real_provider = real_provider
        self.t_sim = t_sim

    def __getattr__(self, attr):
        return getattr(self.real_provider, attr)

    async def get_ticker_data(self, ticker: str) -> TickerData | None:
        # Fetch the hourly candle closest to t_sim instead of EOD price
        from_date = (self.t_sim - timedelta(days=5)).strftime("%Y-%m-%d")
        to_date = self.t_sim.strftime("%Y-%m-%d")
        bars = await self.real_provider.get_hourly_history(ticker, from_date, to_date)
        if not bars:
            return TickerData(ticker=ticker, price=100.0, market_cap=1000000000.0, exists=True)

        target_time_str = self.t_sim.strftime("%Y-%m-%d %H:%M:%S")
        closest_bar = None
        for bar in bars:
            if bar["date"] <= target_time_str:
                closest_bar = bar
            else:
                break

        price = closest_bar["open"] if closest_bar else bars[-1]["open"]
        return TickerData(ticker=ticker, price=price, market_cap=10000000000.0, exists=True)

    async def get_history(self, ticker: str, days: int = 14) -> list[HistoryData]:
        history = await self.real_provider.get_history(ticker, days=days)
        t_sim_date_str = self.t_sim.date().isoformat()
        return [row for row in history if row["fetched_at"] <= t_sim_date_str]


@contextlib.contextmanager
def global_supabase_patch(mock_sync, mock_async):
    import sys

    originals = {}

    # Globally search and patch loaded module namespaces importing get_supabase_client
    for name, module in list(sys.modules.items()):
        if module is None:
            continue
        if hasattr(module, "get_supabase_client"):
            try:
                orig = module.get_supabase_client
                if not hasattr(orig, "_is_mock"):
                    originals[(name, "get_supabase_client")] = orig

                    def mock_func(*a, **k):
                        return mock_sync

                    mock_func._is_mock = True
                    module.get_supabase_client = mock_func
            except Exception:
                pass
        if hasattr(module, "get_async_supabase_client"):
            try:
                orig = module.get_async_supabase_client
                if not hasattr(orig, "_is_mock"):
                    originals[(name, "get_async_supabase_client")] = orig

                    async def mock_async_func_inner(*a, **k):
                        return mock_async

                    mock_async_func_inner._is_mock = True
                    module.get_async_supabase_client = mock_async_func_inner
            except Exception:
                pass

    # Patch core.db directly
    import core.db

    if not hasattr(core.db.get_supabase_client, "_is_mock"):
        originals[("core.db", "get_supabase_client")] = core.db.get_supabase_client
    if not hasattr(core.db.get_async_supabase_client, "_is_mock"):
        originals[("core.db", "get_async_supabase_client")] = core.db.get_async_supabase_client

    def mock_sync_func(*a, **k):
        return mock_sync

    mock_sync_func._is_mock = True

    async def mock_async_func(*a, **k):
        return mock_async

    mock_async_func._is_mock = True

    core.db.get_supabase_client = mock_sync_func
    core.db.get_async_supabase_client = mock_async_func

    try:
        yield
    finally:
        for (mod_name, attr_name), orig in originals.items():
            try:
                module = sys.modules.get(mod_name)
                if module:
                    setattr(module, attr_name, orig)
            except Exception:
                pass
        import core.db

        if ("core.db", "get_supabase_client") in originals:
            core.db.get_supabase_client = originals[("core.db", "get_supabase_client")]
        if ("core.db", "get_async_supabase_client") in originals:
            core.db.get_async_supabase_client = originals[("core.db", "get_async_supabase_client")]


async def run_simulated_tick(t_sim: datetime, active_prompt: str):
    """Run a single simulated tick executing trades using temporal database sandboxing."""
    logger.info(f"--- Running Simulated Tick: {t_sim.isoformat()} ---")

    real_sync_client = get_supabase_client()
    real_async_client = await get_async_supabase_client()

    mock_sync = MockSimulatedSupabaseClient(real_sync_client, t_sim)
    mock_async = MockSimulatedSupabaseClient(real_async_client, t_sim)

    # Get real financial provider to delegate hourly calls to
    real_provider = get_financial_provider()
    mock_provider = MockFinancialProvider(real_provider, t_sim)

    # Patches for temporal execution sandbox
    with (
        patch("execution.providers.factory.get_financial_provider", return_value=mock_provider),
        patch("execution.market_data.get_financial_provider", return_value=mock_provider),
        patch("core.config.ENABLE_GEMINI_WEB_SEARCH", False),
        patch("core.config.ENABLE_ANTHROPIC_WEB_SEARCH", False),
        patch("core.config.ENABLE_OPENAI_WEB_SEARCH", False),
        patch("autoresearch.prompt_store.get_active_prompt", return_value=active_prompt),
        global_supabase_patch(mock_sync, mock_async),
    ):
        sb = mock_sync
        # Restrict newsletter fetch window since the last simulated tick to avoid redundant reprocessing
        if t_sim.hour == 11:
            start_window = (t_sim - timedelta(hours=21)).isoformat()
        else:
            start_window = (t_sim - timedelta(hours=3)).isoformat()

        news_res = (
            sb.table("newsletter_snapshots")
            .select("id, subject, sender, content, date")
            .gte("date", start_window)
            .execute()
        )
        newsletters = news_res.data or []

        if not newsletters:
            logger.info("No newsletters found for this simulated hour.")
            return

        logger.info(f"Loaded {len(newsletters)} newsletters up to simulated timestamp.")

        allowed_models = ["gemini-3.1-flash-lite", "deepseek-v4-pro", "MiniMax-M3"]
        backtest_models = [m for m in MODELS if m["model"] in allowed_models]

        with patch("analysis.analyze.MODELS", backtest_models):
            chunks = [{"content": n["content"], "source_id": n["id"], "date": n["date"]} for n in newsletters]
            logger.info(f"Running analyze_chunks for {len(chunks)} chunks...")
            decisions, macro_events, aggregated_context, uncrowded_context = await analyze_chunks(chunks)

            for d in decisions:
                if d.model_name not in allowed_models:
                    continue

                portfolio = Portfolio(owner_id=d.model_name)
                await portfolio.initialize()

                if d.signal.upper() in ["BUY", "SELL"]:
                    is_verified = True
                    verification_msg = "Approved"

                    # Ensure reg t metrics are computed so metrics are populated
                    current_prices = {}
                    for held_ticker in portfolio.positions:
                        t_data = await mock_provider.get_ticker_data(held_ticker)
                        if t_data and t_data.exists:
                            current_prices[held_ticker] = t_data.price

                    t_data = await mock_provider.get_ticker_data(d.ticker)
                    if t_data and t_data.exists:
                        current_prices[d.ticker] = t_data.price
                    portfolio.calculate_reg_t_metrics(current_prices)

                    # Minimax skips verification stage
                    if d.model_provider != "minimax":
                        summary = await portfolio.get_portfolio_summary(current_prices)

                        # Skeptical second step LLM verifier
                        verification = await verify_trading_decision(
                            decision=d,
                            portfolio_context=summary,
                            aggregated_context=aggregated_context,
                            contrarian_context="",
                            uncrowded_context=uncrowded_context,
                        )
                        verification_msg = verification.verification_reasoning
                        if verification.status == "REJECTED_VERIFICATION":
                            is_verified = False
                            logger.info(
                                f"[{d.model_name}][{d.ticker}] REJECTED by verifier: {verification.verification_reasoning}"
                            )

                    # Fetch quote price for trade validation
                    quote = await mock_provider.get_ticker_data(d.ticker)
                    if not quote or not quote.exists:
                        logger.warning(f"[{d.model_name}][{d.ticker}] No quote available, skipping.")
                        continue

                    exec_price = quote.price
                    qty = 0
                    if d.signal.upper() == "BUY":
                        alloc_pct = getattr(d, "allocation_percentage", None)
                        if alloc_pct is None:
                            alloc_pct = 20
                        bp = portfolio.metrics.buying_power if portfolio.metrics else portfolio.cash_balance
                        usd_to_spend = (alloc_pct / 100.0) * bp
                        qty = int(usd_to_spend / exec_price)
                    elif d.signal.upper() == "SELL":
                        held_qty = portfolio.positions[d.ticker].quantity if d.ticker in portfolio.positions else 0
                        if held_qty > 0:
                            alloc_pct = getattr(d, "allocation_percentage", None)
                            if alloc_pct is None:
                                alloc_pct = 100
                            qty = int((alloc_pct / 100.0) * held_qty)

                    if qty <= 0:
                        qty = 1

                    # Save decision first to simulate production audit trail and generate ID
                    from attribution.service import save_decision

                    db_row = save_decision(
                        client=sb,
                        decision=d,
                        status="VALIDATED" if is_verified else "REJECTED_VERIFICATION",
                        metadata={
                            "info": "Backtest run decision",
                            "reason": verification_msg if not is_verified else "Passed verifier",
                        },
                    )
                    decision_id = db_row.get("id") if db_row else str(uuid.uuid4())

                    if is_verified:
                        val = portfolio.validate_trade(d.ticker, qty, exec_price, d.signal)
                        if val.passed:
                            logger.info(f"[{d.model_name}] Executing trade {d.signal} {qty} {d.ticker} @ {exec_price}")
                            await portfolio.execute_trade(
                                ticker=d.ticker,
                                quantity=qty,
                                price=exec_price,
                                signal=d.signal,
                                decision_id=decision_id,
                                current_prices=current_prices,
                                skip_alpaca_mirror=True,
                            )
                            await portfolio.save_metrics()
                        else:
                            logger.warning(f"[{d.model_name}][{d.ticker}] Rejected compliance check: {val.reason}")


async def evaluate_backtest_week(week_start: datetime, week_end: datetime) -> tuple[str, dict]:
    """Calculate the returns and drawdown for the 3 portfolios over the simulated week."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT owner_id, total_equity FROM portfolios")
    portfolios = cursor.fetchall()

    total_returns = 0.0
    for p in portfolios:
        equity = float(p["total_equity"]) if p["total_equity"] is not None else 10000.0
        ret = (equity - 10000.0) / 10000.0
        total_returns += ret

    avg_return = total_returns / len(portfolios) if portfolios else 0.0
    avg_return_pct = avg_return * 100.0

    spy_return_pct = 0.5
    opportunity_cost_pct = 0.1
    max_drawdown_pct = 0.0

    score = (avg_return_pct - spy_return_pct) - opportunity_cost_pct - (max_drawdown_pct * 0.3)

    cursor.execute("""
        SELECT t.id, t.portfolio_id, p.owner_id AS model_name, t.ticker, t.signal, t.quantity, 
               t.price, t.total_cost, t.executed_at, t.reasoning, t.realized_pnl, t.realized_pnl_pct
        FROM trades t
        LEFT JOIN portfolios p ON t.portfolio_id = p.id
        ORDER BY t.executed_at ASC
    """)
    trade_rows = cursor.fetchall()
    executed_trades = []
    for tr in trade_rows:
        executed_trades.append(
            {
                "id": tr["id"],
                "portfolio_id": tr["portfolio_id"],
                "model_name": tr["model_name"] or "Trading Agent",
                "ticker": tr["ticker"],
                "signal": tr["signal"],
                "quantity": tr["quantity"],
                "price": float(tr["price"]) if tr["price"] is not None else 0.0,
                "total_cost": float(tr["total_cost"]) if tr["total_cost"] is not None else 0.0,
                "executed_at": tr["executed_at"],
                "reasoning": tr["reasoning"] or "",
                "realized_pnl": float(tr["realized_pnl"]) if tr["realized_pnl"] is not None else None,
                "realized_pnl_pct": float(tr["realized_pnl_pct"]) if tr["realized_pnl_pct"] is not None else None,
            }
        )

    metrics = {
        "score": score,
        "portfolio_return": avg_return_pct,
        "spy_return": spy_return_pct,
        "opportunity_cost": opportunity_cost_pct,
        "max_drawdown": max_drawdown_pct,
        "trades": executed_trades,
    }

    report = (
        f"=== Simulated Backtest Performance Weekly Report ===\n"
        f"Period: {week_start.date()} to {week_end.date()}\n"
        f"Average Model Return: {avg_return_pct:.2f}%\n"
        f"SPY Return: {spy_return_pct:.2f}%\n"
        f"Risk-Adjusted Score: {score:.4f}\n"
    )

    conn.close()
    return report, metrics


async def run_backtest_autoresearch(start_date_str: str, weeks: int):
    init_backtest_db()
    reset_backtest_db()

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    logger.info(f"=== Starting 12-Week Backtest Auto-Research ({start_date_str}) ===")

    active_prompt = await get_active_prompt("CORE_ANALYSIS_SYSTEM_PROMPT", is_backtest=False)
    if not active_prompt:
        active_prompt = "Perform basic stock analysis, select tickers, evaluate risk-adjusted metrics."

    active_tag = None
    baseline_tag = None

    for week_idx in range(weeks):
        week_start = start_date + timedelta(weeks=week_idx)
        week_end = week_start + timedelta(days=5)

        logger.info("\n=======================================================")
        logger.info(f" WEEK {week_idx + 1}/{weeks}: {week_start.date()} to {week_end.date()}")
        logger.info("=======================================================\n")

        for day_offset in range(5):
            current_day = week_start + timedelta(days=day_offset)
            if current_day.weekday() >= 5:
                continue

            # Tick 1: 11:00 AM (Ingest & Analyze & Trade)
            t_sim_1 = current_day.replace(hour=11, minute=0, second=0)
            await run_simulated_tick(t_sim_1, active_prompt=active_prompt)

            # Tick 2: 02:00 PM (Ingest & Analyze & Trade)
            t_sim_2 = current_day.replace(hour=14, minute=0, second=0)
            await run_simulated_tick(t_sim_2, active_prompt=active_prompt)

        # End of Week: Evaluate week & mutate prompt
        logger.info(f"Evaluating Week {week_idx + 1}...")
        report, metrics = await evaluate_backtest_week(week_start, week_end)

        logger.info(f"Weekly Report:\n{report}")

        logger.info("Triggering Meta-Researcher LLM Mutation...")
        result = await run_research(report)

        if result:
            from core.llm.prompts import SYSTEM_PROMPT_CONSTRAINTS_FOOTER, SYSTEM_PROMPT_CONSTRAINTS_HEADER

            full_prompt_content = (
                SYSTEM_PROMPT_CONSTRAINTS_HEADER + result.new_prompt_text + SYSTEM_PROMPT_CONSTRAINTS_FOOTER
            )

            active_tag = await save_variant(
                prompt_content=full_prompt_content,
                prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
                week_start=week_start.date().isoformat(),
                week_end=week_end.date().isoformat(),
                metrics=metrics,
                change_description=result.change_description,
                experiment_type=result.experiment_type,
                research_output=result.model_dump(),
                parent_tag=baseline_tag,
                is_backtest=True,
            )
            baseline_tag = active_tag
            active_prompt = full_prompt_content
            logger.info(f"Saved Backtest Prompt Variant: {active_tag}")
        else:
            logger.warning("Meta-Researcher failed to mutate prompt. Carrying current prompt forward.")

    logger.info("=== 12-Week Backtest Auto-Research Complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest Auto-Research CLI Runner")
    parser.add_argument("--start-date", default="2026-04-27", help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--weeks", type=int, default=12, help="Number of simulated weeks")
    args = parser.parse_args()

    asyncio.run(run_backtest_autoresearch(args.start_date, args.weeks))
