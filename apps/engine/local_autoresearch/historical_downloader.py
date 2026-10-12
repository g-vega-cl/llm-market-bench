"""Historical Data Downloader for Offline Local Autoresearch.

Pre-downloads and persists multi-year historical EOD bars, pre-market 5-minute bars,
market news, Gmail newsletters, and macroeconomic series into a local raw SQLite vault,
completely eliminating live network calls and rate limits during research iterations.
"""

from __future__ import annotations

import argparse
import email
import email.utils
import imaplib
import os
import sqlite3
import sys
import time
from datetime import UTC, datetime

import httpx

# Ensure apps/engine root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import FMP_API_KEY, GMAIL_APP_PASSWORD, GMAIL_EMAIL, MASSIVE_API_KEY, logger

DEFAULT_RAW_DB = ".historical_raw.db"
DEFAULT_PROXIES = ["SPY", "QQQ", "DIA", "IWM", "TLT", "IEF", "GLD", "USO", "UUP"]
DEFAULT_FRED_SERIES = ["DGS10", "DGS2", "T10Y2Y", "FEDFUNDS", "UNRATE", "ICSA"]
DEFAULT_PM_SYMBOLS = ["SPY", "QQQ", "IWM", "TLT"]


class TokenBucketLimiter:
    """Synchronous token-bucket rate limiter for external APIs."""

    def __init__(self, max_tokens: float = 5.0, refill_period_seconds: float = 60.0):
        self.capacity = max_tokens
        self.tokens = max_tokens
        self.refill_rate = max_tokens / refill_period_seconds
        self.last_update = time.monotonic()

    def consume(self, tokens: float = 1.0) -> bool:
        """Attempt to consume tokens. Returns True if successful, False otherwise."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_and_consume(self, tokens: float = 1.0) -> None:
        """Block until tokens are available, then consume."""
        while not self.consume(tokens):
            time.sleep(0.1)


def init_raw_db(db_path: str = DEFAULT_RAW_DB) -> None:
    """Initialize SQLite tables for raw historical data vault."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eod_bars (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            vwap REAL,
            PRIMARY KEY (ticker, date)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premarket_bars (
            ticker TEXT NOT NULL,
            bar_time_utc TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            vwap REAL,
            PRIMARY KEY (ticker, bar_time_utc)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_newsletters (
            source_id TEXT PRIMARY KEY,
            date_utc TEXT NOT NULL,
            sender TEXT NOT NULL,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_news (
            id TEXT PRIMARY KEY,
            published_utc TEXT NOT NULL,
            ticker TEXT,
            title TEXT NOT NULL,
            description TEXT,
            publisher TEXT,
            keywords TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macro_series (
            series_id TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL NOT NULL,
            PRIMARY KEY (series_id, date)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_premarket_bars_time ON premarket_bars(ticker, bar_time_utc)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_news_pub ON market_news(published_utc)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_newsletters_date ON raw_newsletters(date_utc)")

    conn.commit()
    conn.close()


def _generate_monthly_chunks(start_str: str, end_str: str) -> list[tuple[str, str]]:
    """Split date range into month-by-month tuples to prevent Polygon result set truncation."""
    from datetime import date, timedelta

    start_d = date.fromisoformat(start_str[:10])
    end_d = date.fromisoformat(end_str[:10])
    chunks = []
    curr = start_d
    while curr <= end_d:
        next_month = date(curr.year + 1, 1, 1) if curr.month == 12 else date(curr.year, curr.month + 1, 1)
        month_end = min(next_month - timedelta(days=1), end_d)
        chunks.append((curr.isoformat(), month_end.isoformat()))
        curr = next_month
    return chunks


class HistoricalDownloader:
    """Orchestrates rate-limited downloads from FMP, Polygon, Gmail, and FRED into SQLite."""

    def __init__(
        self,
        db_path: str = DEFAULT_RAW_DB,
        fmp_api_key: str | None = None,
        massive_api_key: str | None = None,
        gmail_email: str | None = None,
        gmail_password: str | None = None,
    ):
        self.db_path = db_path
        self.fmp_api_key = fmp_api_key or FMP_API_KEY or ""
        self.massive_api_key = massive_api_key or MASSIVE_API_KEY or ""
        self.gmail_email = gmail_email or GMAIL_EMAIL or ""
        self.gmail_password = gmail_password or GMAIL_APP_PASSWORD or ""

        # Rate limiters: pace Polygon at 1 request per 12.5s (4.8 req/min) to prevent 429 rate limit bursts
        self.polygon_limiter = TokenBucketLimiter(max_tokens=1.0, refill_period_seconds=12.5)
        self.fmp_limiter = TokenBucketLimiter(max_tokens=1.0, refill_period_seconds=2.0)
        init_raw_db(self.db_path)

    def download_fmp_eod(self, symbols: list[str], start_date: str, end_date: str) -> int:
        """Download daily EOD bars from FMP for specified tickers and date range."""
        if not self.fmp_api_key:
            logger.warning("FMP_API_KEY missing; skipping FMP EOD download.")
            return 0

        total_inserted = 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        with httpx.Client(timeout=30.0) as client:
            for sym in symbols:
                self.fmp_limiter.wait_and_consume()
                url = "https://financialmodelingprep.com/stable/historical-price-eod/full"
                params = {"symbol": sym.upper(), "from": start_date, "to": end_date, "apikey": self.fmp_api_key}

                try:
                    resp = client.get(url, params=params)
                    if resp.status_code != 200:
                        logger.error(f"FMP EOD failed for {sym}: {resp.status_code} {resp.text[:150]}")
                        continue

                    data = resp.json()
                    rows = data if isinstance(data, list) else data.get("historical", [])
                    records = []
                    for r in rows:
                        records.append(
                            (
                                sym.upper(),
                                r["date"],
                                float(r["open"]),
                                float(r["high"]),
                                float(r["low"]),
                                float(r["close"]),
                                int(r.get("volume", 0)),
                                float(r.get("vwap", r["close"])),
                            )
                        )

                    cursor.executemany(
                        """
                        INSERT OR REPLACE INTO eod_bars (ticker, date, open, high, low, close, volume, vwap)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        records,
                    )
                    conn.commit()
                    total_inserted += len(records)
                    logger.info(f"FMP EOD: Saved {len(records)} bars for {sym}")
                except Exception as ex:
                    logger.exception(f"Error fetching FMP EOD for {sym}: {ex}")

        conn.close()
        return total_inserted

    def download_polygon_bars(self, ticker: str, start_date: str, end_date: str) -> int:
        """Download 5-minute bars (including pre-market) from Polygon in monthly chunks."""
        if not self.massive_api_key:
            logger.warning("MASSIVE_API_KEY missing; skipping Polygon bars download.")
            return 0

        chunks = _generate_monthly_chunks(start_date, end_date)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        total_inserted = 0

        with httpx.Client(timeout=45.0) as client:
            for c_start, c_end in chunks:
                # Check if already cached
                cursor.execute(
                    "SELECT COUNT(*) FROM premarket_bars WHERE ticker = ? AND bar_time_utc >= ? AND bar_time_utc <= ?",
                    (ticker.upper(), f"{c_start}T00:00:00Z", f"{c_end}T23:59:59Z"),
                )
                if cursor.fetchone()[0] > 100:
                    logger.info(f"Polygon bars already cached for {ticker} ({c_start} to {c_end}), skipping.")
                    continue

                for attempt in range(3):
                    self.polygon_limiter.wait_and_consume()
                    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker.upper()}/range/5/minute/{c_start}/{c_end}"
                    params = {"apiKey": self.massive_api_key, "adjusted": "true", "limit": 50000}

                    try:
                        resp = client.get(url, params=params)
                        if resp.status_code == 429:
                            logger.warning(
                                f"Polygon 429 rate limit hit for {ticker} ({c_start}..{c_end}). Backing off 65s (attempt {attempt + 1}/3)..."
                            )
                            time.sleep(65.0)
                            continue
                        if resp.status_code != 200:
                            logger.error(
                                f"Polygon bars failed for {c_start}..{c_end}: {resp.status_code} {resp.text[:150]}"
                            )
                            break

                        data = resp.json()
                        results = data.get("results", [])
                        records = []
                        for b in results:
                            utc_dt = datetime.fromtimestamp(b["t"] / 1000, tz=UTC)
                            iso_time = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                            records.append(
                                (
                                    ticker.upper(),
                                    iso_time,
                                    float(b["o"]),
                                    float(b["h"]),
                                    float(b["l"]),
                                    float(b["c"]),
                                    int(b.get("v", 0)),
                                    float(b.get("vw", b["c"])),
                                )
                            )

                        cursor.executemany(
                            """
                            INSERT OR REPLACE INTO premarket_bars
                            (ticker, bar_time_utc, open, high, low, close, volume, vwap)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            records,
                        )
                        conn.commit()
                        total_inserted += len(records)
                        logger.info(f"Polygon: Saved {len(records)} 5-min bars for {ticker} ({c_start} to {c_end})")
                        break
                    except Exception as ex:
                        logger.exception(f"Error fetching Polygon bars for {ticker}: {ex}")
                        break

        conn.close()
        return total_inserted

    def download_multi_polygon_bars(self, tickers: list[str], start_date: str, end_date: str) -> dict[str, int]:
        """Download 5-minute bars for multiple tickers sequentially respecting rate limits."""
        results: dict[str, int] = {}
        for sym in tickers:
            logger.info(f"Downloading Polygon 5-min bars for {sym} ({start_date} to {end_date})...")
            cnt = self.download_polygon_bars(sym, start_date, end_date)
            results[sym] = cnt
        return results

    def download_polygon_news(self, start_utc: str, end_utc: str, ticker: str | None = None) -> int:
        """Download point-in-time reference news from Polygon."""
        if not self.massive_api_key:
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        total_inserted = 0

        with httpx.Client(timeout=30.0) as client:
            self.polygon_limiter.wait_and_consume()
            url = "https://api.polygon.io/v2/reference/news"
            params: dict[str, str | int] = {
                "published_utc.gte": start_utc,
                "published_utc.lte": end_utc,
                "limit": 1000,
                "apiKey": self.massive_api_key,
            }
            if ticker:
                params["ticker"] = ticker.upper()

            try:
                resp = client.get(url, params=params)
                if resp.status_code != 200:
                    logger.error(f"Polygon news failed: {resp.status_code} {resp.text[:150]}")
                    conn.close()
                    return 0

                results = resp.json().get("results", [])
                records = []
                for item in results:
                    records.append(
                        (
                            item.get("id", f"poly_{item.get('published_utc')}_{len(records)}"),
                            item.get("published_utc"),
                            ticker or "MARKET",
                            item.get("title", ""),
                            item.get("description", "") or "",
                            item.get("publisher", {}).get("name", "Unknown"),
                            ",".join(item.get("keywords", [])),
                        )
                    )

                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO market_news
                    (id, published_utc, ticker, title, description, publisher, keywords)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    records,
                )
                conn.commit()
                total_inserted += len(records)
                logger.info(f"Polygon: Saved {len(records)} news articles ({start_utc} to {end_utc})")
            except Exception as ex:
                logger.exception(f"Error fetching Polygon news: {ex}")

        conn.close()
        return total_inserted

    def download_gmail_newsletters(self, start_date: str, end_date: str) -> int:
        """Download and clean financial newsletters from Gmail via IMAP."""
        if not self.gmail_email or not self.gmail_password:
            logger.warning("Gmail credentials missing; skipping newsletter download.")
            return 0

        from ingest.newsletter import NEWSLETTER_SENDERS, clean_text, extract_email_message_body

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        total_inserted = 0

        clean_pwd = self.gmail_password.replace(" ", "")
        sender_filter = " OR ".join(NEWSLETTER_SENDERS)
        q = f"from:({sender_filter}) before:{end_date} after:{start_date}"

        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(self.gmail_email, clean_pwd)
            mail.select("INBOX", readonly=True)

            status, data = mail.search(None, f'X-GM-RAW "{q}"')
            if status != "OK" or not data or not data[0]:
                mail.close()
                mail.logout()
                conn.close()
                return 0

            msg_ids = data[0].split()
            logger.info(f"Found {len(msg_ids)} newsletter emails in Gmail for {start_date} to {end_date}")

            records = []
            for mid in msg_ids:
                res, msg_data = mail.fetch(mid, "(RFC822)")
                if res != "OK" or not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple):
                    continue

                raw_msg = email.message_from_bytes(msg_data[0][1])
                sub = raw_msg.get("Subject", "No Subject")
                snd = raw_msg.get("From", "Unknown")
                raw_dt = raw_msg.get("Date", "")
                try:
                    dt = email.utils.parsedate_to_datetime(raw_dt)
                    utc_iso = dt.astimezone(UTC).isoformat()
                except Exception:
                    utc_iso = datetime.now(UTC).isoformat()

                body = extract_email_message_body(raw_msg)
                clean_body = clean_text(body)
                src_id = f"gmail_{utc_iso}_{snd}_{hash(sub)}"

                records.append(
                    (
                        src_id,
                        utc_iso,
                        snd,
                        sub,
                        clean_body,
                        datetime.now(UTC).isoformat(),
                    )
                )

            cursor.executemany(
                """
                INSERT OR REPLACE INTO raw_newsletters
                (source_id, date_utc, sender, subject, content, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()
            total_inserted += len(records)
            logger.info(f"Gmail: Ingested {len(records)} clean newsletters into raw vault.")

            mail.close()
            mail.logout()
        except Exception as ex:
            logger.exception(f"Error fetching Gmail newsletters: {ex}")

        conn.close()
        return total_inserted

    def download_fred_series(self, series_ids: list[str]) -> int:
        """Download historical macroeconomic series from FRED direct CSV."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        total_inserted = 0

        with httpx.Client(timeout=30.0) as client:
            for s_id in series_ids:
                url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s_id}"
                try:
                    resp = client.get(url)
                    if resp.status_code != 200:
                        continue

                    records = []
                    lines = resp.text.strip().split("\n")
                    for line in lines[1:]:  # skip header
                        parts = line.split(",")
                        if len(parts) >= 2 and parts[1] != ".":
                            try:
                                val = float(parts[1])
                                records.append((s_id, parts[0], val))
                            except ValueError:
                                continue

                    cursor.executemany(
                        """
                        INSERT OR REPLACE INTO macro_series (series_id, date, value)
                        VALUES (?, ?, ?)
                        """,
                        records,
                    )
                    conn.commit()
                    total_inserted += len(records)
                    logger.info(f"FRED: Saved {len(records)} observations for {s_id}")
                except Exception as ex:
                    logger.exception(f"Error fetching FRED series {s_id}: {ex}")

        conn.close()
        return total_inserted


def sync_to_local_postgres(db_path: str = DEFAULT_RAW_DB) -> dict[str, int]:
    """Sync raw SQLite tables to local Docker PostgreSQL (market-bench-archive-db)."""
    import subprocess

    if not os.path.exists(db_path):
        logger.error(f"Cannot sync: {db_path} does not exist.")
        return {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stats: dict[str, int] = {}
    table_mappings = [
        ("eod_bars", "historical_eod_bars", ["ticker", "date", "open", "high", "low", "close", "volume", "vwap"]),
        (
            "premarket_bars",
            "historical_premarket_bars",
            ["ticker", "bar_time_utc", "open", "high", "low", "close", "volume", "vwap"],
        ),
        (
            "raw_newsletters",
            "historical_raw_newsletters",
            ["source_id", "date_utc", "sender", "subject", "content", "ingested_at"],
        ),
        (
            "market_news",
            "historical_market_news",
            ["id", "published_utc", "ticker", "title", "description", "publisher", "keywords"],
        ),
        ("macro_series", "historical_macro_series", ["series_id", "date", "value"]),
    ]

    for src_tbl, dst_tbl, cols in table_mappings:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {src_tbl}")
            count = cursor.fetchone()[0]
        except Exception:
            continue

        stats[dst_tbl] = count
        if count == 0:
            continue

        cursor.execute(f"SELECT {', '.join(cols)} FROM {src_tbl}")
        rows = cursor.fetchall()

        sql_lines = []
        for r in rows:
            vals = []
            for col in cols:
                v = r[col]
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    escaped = str(v).replace("'", "''")
                    vals.append(f"'{escaped}'")
            sql_lines.append(f"({', '.join(vals)})")

        batch_size = 500
        for i in range(0, len(sql_lines), batch_size):
            chunk = sql_lines[i : i + batch_size]
            query = (
                f"INSERT INTO public.{dst_tbl} ({', '.join(cols)}) VALUES {', '.join(chunk)} ON CONFLICT DO NOTHING;\n"
            )
            proc = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    "market-bench-archive-db",
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "market_bench_archive",
                ],
                input=query,
                text=True,
                capture_output=True,
            )
            if proc.returncode != 0:
                logger.error(f"Error syncing {dst_tbl} to local postgres: {proc.stderr[:200]}")

    conn.close()
    logger.info(f"Synced {stats} into local postgres market-bench-archive-db.")
    return stats


def main():
    """CLI entrypoint for standalone historical downloading."""
    parser = argparse.ArgumentParser(description="Download raw historical data for local autoresearch.")
    parser.add_argument("--db-path", default=DEFAULT_RAW_DB, help="SQLite database path")
    parser.add_argument("--symbols", default=",".join(DEFAULT_PROXIES), help="Comma-separated symbols")
    parser.add_argument(
        "--pm-symbols", default=",".join(DEFAULT_PM_SYMBOLS), help="Comma-separated symbols for Polygon 5-min bars"
    )
    parser.add_argument("--start-date", default="2024-10-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2026-10-10", help="End date (YYYY-MM-DD)")
    parser.add_argument("--include-newsletters", action="store_true", help="Include Gmail IMAP ingestion")
    parser.add_argument("--include-news", action="store_true", help="Include Polygon reference news")
    parser.add_argument("--sync-postgres", action="store_true", help="Sync data to local docker PostgreSQL container")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    pm_symbols = [s.strip().upper() for s in args.pm_symbols.split(",") if s.strip()]
    downloader = HistoricalDownloader(db_path=args.db_path)

    print(f"Starting historical download into {args.db_path}...")
    print(f"Timeframe: {args.start_date} to {args.end_date} for symbols: {symbols}")

    eod_cnt = downloader.download_fmp_eod(symbols, args.start_date, args.end_date)
    print(f"Downloaded {eod_cnt} EOD bars across {len(symbols)} tickers.")

    poly_stats = downloader.download_multi_polygon_bars(pm_symbols, args.start_date, args.end_date)
    print(f"Downloaded Polygon 5-min bars: {poly_stats}")

    fred_cnt = downloader.download_fred_series(DEFAULT_FRED_SERIES)
    print(f"Downloaded {fred_cnt} FRED observations.")

    if args.include_news:
        news_cnt = downloader.download_polygon_news(
            f"{args.start_date}T00:00:00Z", f"{args.end_date}T23:59:59Z", ticker="SPY"
        )
        print(f"Downloaded {news_cnt} Polygon news articles.")

    if args.include_newsletters:
        gmail_cnt = downloader.download_gmail_newsletters(
            args.start_date.replace("-", "/"), args.end_date.replace("-", "/")
        )
        print(f"Downloaded {gmail_cnt} Gmail newsletters.")

    if args.sync_postgres:
        print("Syncing tables to local Docker PostgreSQL (market-bench-archive-db)...")
        stats = sync_to_local_postgres(args.db_path)
        print(f"PostgreSQL sync stats: {stats}")

    print("Historical download complete!")


if __name__ == "__main__":
    main()
