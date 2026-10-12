"""Historical Feature Cache Builder for Local Autoresearch.

Pre-materializes historical point-in-time market data into a local SQLite DB,
enabling hermetic, sub-second iteration loops without repeated network queries.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import date
from typing import Any

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger

DEFAULT_CACHE_DB = ".local_autoresearch_cache.db"


def init_cache_db(db_path: str = DEFAULT_CACHE_DB) -> None:
    """Initialize local SQLite database for historical daily feature cache."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_days (
            target_date TEXT PRIMARY KEY,
            week_key TEXT NOT NULL,
            ticker TEXT NOT NULL DEFAULT 'SPY',
            open_price REAL NOT NULL,
            close_price REAL NOT NULL,
            actual_direction TEXT NOT NULL,
            day_data_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_days_week ON cached_days(week_key)")

    conn.commit()
    conn.close()


def get_iso_week_key(date_str: str) -> str:
    """Return ISO calendar week key (e.g. '2026-W34') for atomic weekly grouping."""
    d = date.fromisoformat(date_str)
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def save_cached_day(day_record: dict[str, Any], db_path: str = DEFAULT_CACHE_DB) -> None:
    """Insert or update a single historical trading day in local SQLite cache."""
    init_cache_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    target_date = day_record["target_date"]
    week_key = get_iso_week_key(target_date)
    ticker = day_record.get("ticker", "SPY")
    open_p = float(day_record.get("open_price", 0.0))
    close_p = float(day_record.get("close_price", 0.0))
    actual_dir = str(day_record.get("actual_direction", "UP" if close_p >= open_p else "DOWN")).upper()

    cursor.execute(
        """
        INSERT OR REPLACE INTO cached_days (
            target_date, week_key, ticker, open_price, close_price,
            actual_direction, day_data_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            target_date,
            week_key,
            ticker,
            open_p,
            close_p,
            actual_dir,
            json.dumps(day_record),
        ),
    )
    conn.commit()
    conn.close()


def load_cached_weeks(db_path: str = DEFAULT_CACHE_DB) -> dict[str, list[dict[str, Any]]]:
    """Load all cached trading days grouped by atomic calendar week.

    Returns:
        dict: Mapping from week_key (e.g. '2026-W34') to list of day records.
    """
    init_cache_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT target_date, week_key, day_data_json
        FROM cached_days
        ORDER BY target_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    weeks: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        w_key = r["week_key"]
        data = json.loads(r["day_data_json"])
        weeks.setdefault(w_key, []).append(data)

    return weeks


def _extract_section(context: str, markers: list[str] | str) -> str:
    """Extract section text starting after marker until the next === header."""
    if isinstance(markers, str):
        markers = [markers]
    for marker in markers:
        if marker not in context:
            continue
        after = context.split(marker, 1)[1]
        lines = after.split("\n")
        start_idx = 1 if lines and ("===" in lines[0] or not lines[0].strip()) else 0
        body = []
        for line in lines[start_idx:]:
            if line.strip().startswith("==="):
                break
            body.append(line)
        res = "\n".join(body).strip()
        if res:
            return res
    return ""


def extract_features_from_prediction_record(
    pred: dict[str, Any], newsletters: list[dict] | None = None
) -> dict[str, Any]:
    """Parse and normalize an evaluated daily_predictions row into a standard day_record."""
    target_date = pred["target_date"]
    open_p = pred.get("actual_open_price") or pred.get("open_price") or 500.0
    close_p = pred.get("actual_close_price") or pred.get("close_price") or 500.0
    actual_dir = pred.get("actual_direction") or ("UP" if close_p >= open_p else "DOWN")

    context = pred.get("market_context") or ""

    econ = _extract_section(
        context,
        [
            "TODAY'S ECONOMIC RELEASES",
            "TODAY'S HIGH-IMPACT ECONOMIC RELEASES",
            "ECONOMIC RELEASES & MACRO PRINTS",
        ],
    )
    synth_news = _extract_section(
        context,
        [
            "AI WALL STREET SYNTHESIZED",
            "Morning Newsletter Briefing:",
            "SYNTHESIZED DAILY NEWSLETTER",
        ],
    )
    options_skew = _extract_section(
        context,
        [
            "Macro Options Sentiment",
            "Options Derivatives Positioning",
        ],
    )
    intraday_p = _extract_section(
        context,
        [
            "INTRADAY MOVEMENT PROFILE",
            "Prior Session Intraday",
        ],
    )
    proxies: dict[str, dict[str, float]] = {}

    # Extract default proxies from context lines if present
    for sym in ["QQQ", "DIA", "IWM", "TLT", "IEF", "GLD", "USO", "UUP"]:
        if f"- {sym}" in context:
            try:
                line = [ln for ln in context.split("\n") if f"- {sym}" in ln][0]
                price_str = line.split("$")[1].split(" ")[0]
                chg_str = line.split("(")[1].split("%")[0]
                proxies[sym] = {"price": float(price_str), "change_pct": float(chg_str)}
            except Exception:
                proxies[sym] = {"price": 100.0, "change_pct": 0.0}

    high_p = pred.get("actual_high_price") or pred.get("high_price") or max(float(open_p), float(close_p))
    low_p = pred.get("actual_low_price") or pred.get("low_price") or min(float(open_p), float(close_p))

    return {
        "target_date": target_date,
        "ticker": pred.get("ticker", "SPY"),
        "open_price": float(open_p),
        "high_price": float(high_p),
        "low_price": float(low_p),
        "close_price": float(close_p),
        "actual_direction": actual_dir.upper(),
        "economic_calendar": econ,
        "synthetic_newsletter": synth_news,
        "newsletters": newsletters or [],
        "proxies": proxies,
        "options_sentiment": options_skew,
        "intraday_profile": intraday_p,
    }


async def build_cache_from_supabase(
    client,
    limit_days: int = 300,
    db_path: str = DEFAULT_CACHE_DB,
) -> int:
    """Extract evaluated historical predictions and point-in-time newsletters from Supabase into local cache."""
    init_cache_db(db_path)

    try:
        # Read evaluated predictions (SPY only, non-backtest)
        resp = (
            client.table("daily_predictions")
            .select("*")
            .eq("ticker", "SPY")
            .eq("status", "evaluated")
            .order("target_date", desc=True)
            .limit(limit_days)
            .execute()
        )
        preds = [
            p
            for p in (resp.data or [])
            if not (p.get("prompt_variant_tag") and "backtest" in p["prompt_variant_tag"].lower())
        ]
        if not preds:
            logger.warning("No evaluated daily predictions found in Supabase.")
            return 0

        logger.info(f"Loaded {len(preds)} evaluated predictions from Supabase. Materializing local cache...")

        count = 0
        for p in preds:
            t_date = p["target_date"]

            # Pull newsletters strictly prior to 09:15 ET on target_date
            news_resp = (
                client.table("newsletter_snapshots")
                .select("sender, subject, content, date")
                .gte("date", f"{t_date}T00:00:00Z")
                .lte("date", f"{t_date}T13:15:00Z")  # 09:15 AM ET is 13:15 UTC (or 14:15 daylight)
                .limit(20)
                .execute()
            )
            raw_news = news_resp.data or []

            day_rec = extract_features_from_prediction_record(p, newsletters=raw_news)

            # Fallback for synthetic newsletter if not captured in legacy market_context
            if not day_rec.get("synthetic_newsletter"):
                try:
                    gen_resp = (
                        client.table("generated_newsletters")
                        .select("summary, bullet_points, content")
                        .gte("created_at", f"{t_date}T00:00:00")
                        .lte("created_at", f"{t_date}T23:59:59")
                        .limit(1)
                        .execute()
                    )
                    if gen_resp and gen_resp.data:
                        row = gen_resp.data[0]
                        bullets = "\n".join([f"- {b}" for b in (row.get("bullet_points") or [])])
                        day_rec["synthetic_newsletter"] = f"{row.get('summary', '')}\n{bullets}".strip()
                except Exception as ex:
                    logger.debug(f"Could not fetch generated newsletter fallback for {t_date}: {ex}")

            save_cached_day(day_rec, db_path=db_path)
            count += 1

        logger.info(f"Successfully cached {count} historical trading days in {db_path}.")
        return count
    except Exception as e:
        logger.error(f"Error building local cache from Supabase: {e}")
        return 0


def build_cache_from_raw_db(
    raw_db_path: str,
    cache_db_path: str = DEFAULT_CACHE_DB,
    start_date: str | None = None,
    end_date: str | None = None,
    is_regime_vault: bool = False,
) -> int:
    """Materialize point-in-time training/test days from local raw SQLite database into cache.

    Guarantees:
    - Zero lookahead: All features strictly timestamped <= 09:15 AM ET on target_date.
    - Regime Vault mode: Pre-market tape is omitted completely without 09:30 open leakage.
    """
    init_cache_db(cache_db_path)
    if not os.path.exists(raw_db_path):
        logger.error(f"Raw database not found at {raw_db_path}")
        return 0

    conn = sqlite3.connect(raw_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query all SPY EOD bars ordered chronologically
    cursor.execute("""
        SELECT ticker, date, open, high, low, close, volume, vwap
        FROM eod_bars
        WHERE ticker = 'SPY'
        ORDER BY date ASC
    """)
    all_eod_rows = cursor.fetchall()

    if not all_eod_rows:
        logger.warning(f"No SPY EOD bars found in {raw_db_path}")
        conn.close()
        return 0

    count = 0
    # Process each day starting from index 1 (so index 0 provides prior day setup)
    for i in range(1, len(all_eod_rows)):
        target_row = all_eod_rows[i]
        t_date = target_row["date"]

        if start_date and t_date < start_date:
            continue
        if end_date and t_date > end_date:
            continue

        prior_row = all_eod_rows[i - 1]
        prev_date = prior_row["date"]

        # 1. Prior day technical profile (fully realized at T-1 16:00 ET)
        p_open = float(prior_row["open"])
        p_high = float(prior_row["high"])
        p_low = float(prior_row["low"])
        p_close = float(prior_row["close"])
        p_vwap = float(prior_row["vwap"] or p_close)
        clv = ((2.0 * p_close - p_high - p_low) / (p_high - p_low)) if (p_high > p_low) else 0.0

        intraday_profile = (
            f"=== PRIOR SESSION TECHNICAL PROFILE ({prev_date}) ===\n"
            f"- Close: ${p_close:.2f} | High: ${p_high:.2f} | Low: ${p_low:.2f} | Open: ${p_open:.2f}\n"
            f"- Prior Session VWAP: ${p_vwap:.2f} | CLV: {clv:+.2f}"
        )

        # 2. Overnight window timestamps: (T-1 16:00 ET / 20:00 UTC) to (T 09:15 ET / 13:15 UTC)
        cutoff_start = f"{prev_date}T20:00:00Z"
        cutoff_end = f"{t_date}T13:15:00Z"

        # Newsletters
        cursor.execute(
            """
            SELECT sender, subject, content, date_utc
            FROM raw_newsletters
            WHERE date_utc >= ? AND date_utc <= ?
            ORDER BY date_utc ASC
            """,
            (cutoff_start, cutoff_end),
        )
        newsletters = [dict(r) for r in cursor.fetchall()]

        # Market news
        cursor.execute(
            """
            SELECT id, published_utc, ticker, title, description, publisher
            FROM market_news
            WHERE published_utc >= ? AND published_utc <= ?
            ORDER BY published_utc ASC
            """,
            (cutoff_start, cutoff_end),
        )
        market_news = [dict(r) for r in cursor.fetchall()]

        # 3. Pre-market quotes & proxy gaps
        proxies: dict[str, dict[str, float]] = {}
        if not is_regime_vault:
            # Query premarket bar for SPY closing on or before 13:15:00Z (09:15 ET)
            cursor.execute(
                """
                SELECT close, bar_time_utc
                FROM premarket_bars
                WHERE ticker = 'SPY' AND bar_time_utc >= ? AND bar_time_utc <= ?
                ORDER BY bar_time_utc DESC
                LIMIT 1
                """,
                (f"{t_date}T00:00:00Z", cutoff_end),
            )
            pm_bar = cursor.fetchone()
            if pm_bar:
                pm_px = float(pm_bar["close"])
                pm_gap = ((pm_px - p_close) / p_close) * 100.0
                proxies["SPY"] = {"price": pm_px, "change_pct": round(pm_gap, 2)}

            # Also check macro proxy premarket gaps if available
            for sym in ["QQQ", "DIA", "IWM", "TLT", "IEF", "GLD", "USO", "UUP"]:
                cursor.execute(
                    """
                    SELECT close FROM premarket_bars
                    WHERE ticker = ? AND bar_time_utc >= ? AND bar_time_utc <= ?
                    ORDER BY bar_time_utc DESC LIMIT 1
                    """,
                    (sym, f"{t_date}T00:00:00Z", cutoff_end),
                )
                sym_bar = cursor.fetchone()
                if sym_bar:
                    sym_px = float(sym_bar["close"])
                    # Query prior EOD for this sym
                    cursor.execute(
                        "SELECT close FROM eod_bars WHERE ticker = ? AND date = ?",
                        (sym, prev_date),
                    )
                    sym_prev = cursor.fetchone()
                    sym_prev_c = float(sym_prev["close"]) if sym_prev else sym_px
                    sym_gap = ((sym_px - sym_prev_c) / sym_prev_c) * 100.0 if sym_prev_c else 0.0
                    proxies[sym] = {"price": sym_px, "change_pct": round(sym_gap, 2)}

        # 4. Macroeconomic rates & calendar (FRED) strictly point-in-time <= prev_date
        cursor.execute(
            """
            SELECT series_id, value, date
            FROM macro_series
            WHERE date <= ?
            ORDER BY date DESC
            """,
            (prev_date,),
        )
        macro_rows = cursor.fetchall()
        macro_dict: dict[str, list[tuple[float, str]]] = {}
        for mr in macro_rows:
            s_id = mr["series_id"]
            if s_id not in macro_dict:
                macro_dict[s_id] = []
            if len(macro_dict[s_id]) < 2:
                macro_dict[s_id].append((float(mr["value"]), mr["date"]))

        econ_lines = []
        if "DGS10" in macro_dict and macro_dict["DGS10"]:
            y10 = macro_dict["DGS10"][0][0]
            d10 = (y10 - macro_dict["DGS10"][1][0]) * 100.0 if len(macro_dict["DGS10"]) > 1 else 0.0
            econ_lines.append(f"- 10-Year Treasury Yield: {y10:.2f}% (1-Day change: {d10:+.1f} bps)")

        if "DGS2" in macro_dict and macro_dict["DGS2"]:
            y2 = macro_dict["DGS2"][0][0]
            d2 = (y2 - macro_dict["DGS2"][1][0]) * 100.0 if len(macro_dict["DGS2"]) > 1 else 0.0
            econ_lines.append(f"- 2-Year Treasury Yield: {y2:.2f}% (1-Day change: {d2:+.1f} bps)")

        if "T10Y2Y" in macro_dict and macro_dict["T10Y2Y"]:
            spread = macro_dict["T10Y2Y"][0][0]
            spread_status = "Inverted" if spread < 0 else "Normal / Steepening"
            econ_lines.append(f"- 10Y-2Y Spread: {spread:+.2f}% ({spread_status})")

        if "FEDFUNDS" in macro_dict and macro_dict["FEDFUNDS"]:
            econ_lines.append(f"- Fed Funds Effective Rate: {macro_dict['FEDFUNDS'][0][0]:.2f}%")

        if "ICSA" in macro_dict and macro_dict["ICSA"]:
            claims_val = int(macro_dict["ICSA"][0][0])
            econ_lines.append(f"- Initial Jobless Claims: {claims_val:,}")

        if "UNRATE" in macro_dict and macro_dict["UNRATE"]:
            econ_lines.append(f"- Civilian Unemployment Rate: {macro_dict['UNRATE'][0][0]:.1f}%")

        economic_calendar = "\n".join(econ_lines)

        # 5. Synthetic newsletter digest
        synthetic_newsletter = ""
        if newsletters:
            top_headlines = [f"[{nl['sender']}] {nl.get('subject', '')}" for nl in newsletters[:4]]
            synthetic_newsletter = "Morning Newsletter Digest:\n" + "\n".join(f"- {h}" for h in top_headlines)

        # 6. Options sentiment proxy derived from prior CLV and session range
        options_sentiment = (
            f"SPY Prior Session Positioning: CLV={clv:+.2f} | "
            f"Close vs VWAP=${p_close - p_vwap:+.2f} | "
            f"Range=${p_high - p_low:.2f}"
        )

        # 7. Target day outcome
        open_price = float(target_row["open"])
        close_price = float(target_row["close"])
        high_price = float(target_row["high"])
        low_price = float(target_row["low"])
        actual_direction = "UP" if close_price >= open_price else "DOWN"

        day_rec: dict[str, Any] = {
            "target_date": t_date,
            "ticker": "SPY",
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "close_price": close_price,
            "actual_direction": actual_direction,
            "economic_calendar": economic_calendar,
            "synthetic_newsletter": synthetic_newsletter,
            "newsletters": newsletters,
            "market_news": market_news,
            "proxies": proxies,
            "options_sentiment": options_sentiment,
            "intraday_profile": intraday_profile,
        }

        save_cached_day(day_rec, db_path=cache_db_path)
        count += 1

    conn.close()
    logger.info(f"Built cache with {count} trading days into {cache_db_path} (regime_vault={is_regime_vault})")
    return count
