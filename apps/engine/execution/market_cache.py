"""Database-backed price and history caching layer.

Coordinates persistence with Supabase for:
1. Short-term quote snapshots in `market_data_cache` (TTL-aware)
2. Historical EOD bars in `price_history` (OHLCV-aware, 24h staleness check for fallbacks)
"""

import datetime
import math

from dateutil import parser as date_parser

from core.config import MARKET_DATA_CACHE_TTL_SECONDS, logger
from core.db import get_supabase_client

from .market_transforms import validate_date_coverage
from .providers.base import TickerData


class MarketDataCache:
    """Manages live quote snapshots and historical price bars in Supabase."""

    def __init__(self, client=None, cache_ttl_seconds: int | None = None):
        self.client = client if client is not None else get_supabase_client()
        self.cache_ttl_seconds = cache_ttl_seconds if cache_ttl_seconds is not None else MARKET_DATA_CACHE_TTL_SECONDS

    def get_quote(self, ticker: str) -> TickerData | None:
        """Retrieve and validate a cached quote from market_data_cache."""
        try:
            response = self.client.table("market_data_cache").select("*").eq("ticker", ticker).execute()

            if not response.data:
                return None

            record = response.data[0]
            fetched_at = datetime.datetime.fromisoformat(record["fetched_at"].replace("Z", "+00:00"))
            now = datetime.datetime.now(datetime.UTC)

            if (now - fetched_at).total_seconds() > self.cache_ttl_seconds:
                logger.debug(f"Cache entry for {ticker} is stale.")
                return None

            return TickerData(
                ticker=record["ticker"],
                price=float(record["price"]),
                market_cap=float(record["market_cap"]) if record.get("market_cap") else 0,
                exists=True,
            )
        except Exception as e:
            logger.error(f"Error reading market data cache for {ticker}: {e}")
            return None

    def get_quotes_batch(self, tickers: list[str]) -> tuple[dict[str, TickerData], list[str]]:
        """Retrieve fresh quotes for multiple tickers, returning (results, missing_tickers)."""
        results: dict[str, TickerData] = {}
        missing_tickers = list(tickers)

        try:
            response = self.client.table("market_data_cache").select("*").in_("ticker", tickers).execute()
            if response.data:
                now = datetime.datetime.now(datetime.UTC)
                for record in response.data:
                    ticker = record["ticker"]
                    fetched_at = datetime.datetime.fromisoformat(record["fetched_at"].replace("Z", "+00:00"))
                    if (now - fetched_at).total_seconds() <= self.cache_ttl_seconds:
                        results[ticker] = TickerData(
                            ticker=ticker,
                            price=float(record["price"]),
                            market_cap=float(record["market_cap"]) if record.get("market_cap") else 0,
                            exists=True,
                        )
                        if ticker in missing_tickers:
                            missing_tickers.remove(ticker)
                    else:
                        logger.debug(f"Cache entry for {ticker} is stale.")
        except Exception as e:
            logger.error(f"Error reading market data cache batch: {e}")

        return results, missing_tickers

    def save_quote(self, data: TickerData) -> None:
        """Upsert a single ticker quote into the live price cache."""
        self.save_quotes_batch([data])

    def save_quotes_batch(self, data_list: list[TickerData]) -> None:
        """Upsert multiple data points into the live price cache."""
        try:
            now_iso = datetime.datetime.now(datetime.UTC).isoformat()
            cache_payloads = []

            for data in data_list:
                if math.isnan(data.price) or math.isnan(data.market_cap):
                    logger.warning(f"Skipping cache save for {data.ticker} due to NaN values.")
                    continue

                payload = {
                    "ticker": data.ticker.strip(),
                    "price": data.price,
                    "market_cap": data.market_cap,
                    "fetched_at": now_iso,
                }
                if data.change_pct is not None:
                    payload["today_pct_change"] = data.change_pct
                elif data.previous_close is not None and data.previous_close > 0:
                    payload["today_pct_change"] = ((data.price - data.previous_close) / data.previous_close) * 100

                cache_payloads.append(payload)

            if cache_payloads:
                self.client.table("market_data_cache").upsert(cache_payloads).execute()

        except Exception as e:
            tickers = [d.ticker for d in data_list]
            logger.error(f"Error saving market data batch for {tickers}: {e}")

    def get_last_known_price(self, ticker: str) -> TickerData | None:
        """Retrieves the most recent price from the history table with a 24h staleness check."""
        try:
            response = (
                self.client.table("price_history")
                .select("*")
                .eq("ticker", ticker)
                .order("fetched_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                record = response.data[0]
                fetched_at_str = record.get("fetched_at", "")
                if fetched_at_str:
                    try:
                        fetched_at = date_parser.isoparse(fetched_at_str)
                        if fetched_at.tzinfo is None:
                            fetched_at = fetched_at.replace(tzinfo=datetime.UTC)

                        now = datetime.datetime.now(datetime.UTC)
                        age_hours = (now - fetched_at).total_seconds() / 3600

                        if age_hours > 24:
                            logger.warning(f"Last known price for {ticker} is stale ({age_hours:.1f}h old). Rejecting.")
                            return None
                    except Exception as parse_err:
                        logger.error(f"Error parsing fetched_at for {ticker}: {parse_err}")
                        return None

                return TickerData(
                    ticker=record["ticker"],
                    price=float(record["price"]),
                    market_cap=float(record["market_cap"]) if record.get("market_cap") else 0,
                    exists=True,
                )
        except Exception as e:
            logger.error(f"Error fetching last known price for {ticker}: {e}")

        return None

    def get_history(self, ticker: str, days: int = 14) -> list[dict] | None:
        """Fetch historical price data from local DB if valid coverage exists.

        Returns:
            List of OHLCV dicts if valid, None if cache miss or coverage invalid.
        """
        try:
            res = (
                self.client.table("price_history")
                .select("price, open, high, low, close, volume, fetched_at")
                .eq("ticker", ticker)
                .order("fetched_at", desc=True)
                .limit(days)
                .execute()
            )

            if res.data and len(res.data) >= (days * 0.7):
                is_valid, reason = validate_date_coverage(res.data, days)
                if is_valid:
                    logger.debug(f"Using local price history for {ticker} ({len(res.data)} samples, {reason}).")
                    return [
                        {
                            "price": float(row["price"]),
                            "open": float(row["open"]) if row.get("open") is not None else None,
                            "high": float(row["high"]) if row.get("high") is not None else None,
                            "low": float(row["low"]) if row.get("low") is not None else None,
                            "close": float(row["close"]) if row.get("close") is not None else None,
                            "volume": int(row["volume"]) if row.get("volume") is not None else None,
                            "fetched_at": row["fetched_at"],
                        }
                        for row in res.data
                    ]
                else:
                    logger.debug(f"Skipping local cache for {ticker}: {reason}. Fetching from provider.")
        except Exception as e:
            logger.warning(f"Error checking local price history for {ticker}: {e}")

        return None

    def save_history(self, ticker: str, history: list[dict]) -> None:
        """Batch upsert OHLCV bars into price_history table."""
        try:
            payloads = []
            for entry in history:
                payload = {
                    "ticker": ticker,
                    "price": float(entry["price"]),
                    "fetched_at": entry["fetched_at"],
                    "market_cap": entry.get("market_cap", 0),
                }
                if entry.get("open") is not None:
                    payload["open"] = float(entry["open"])
                if entry.get("high") is not None:
                    payload["high"] = float(entry["high"])
                if entry.get("low") is not None:
                    payload["low"] = float(entry["low"])
                if entry.get("close") is not None:
                    payload["close"] = float(entry["close"])
                elif entry.get("price") is not None:
                    payload["close"] = float(entry["price"])
                if entry.get("volume") is not None:
                    payload["volume"] = int(entry["volume"])
                payloads.append(payload)

            if payloads:
                self.client.table("price_history").upsert(payloads, on_conflict="ticker, fetched_at").execute()
        except Exception as e:
            logger.warning(f"Error saving historical data for {ticker} to cache: {e}")
