"""Daily Market Document Generator using Qwen via Strata with Cloud Fallback."""

from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
from contextlib import closing
from typing import Any

import httpx

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from local_autoresearch.strata_client import DEFAULT_STRATA_MODEL, DEFAULT_STRATA_URL

DEFAULT_INGESTION_SYSTEM_PROMPT = """You are an elite quantitative market intelligence analyst.
Your objective is to distill raw pre-market feeds, multi-day trend vectors, historical lessons, overnight benchmarks, economic releases, and institutional newsletters into a concise, high-density market briefing document (200 to 240 words, under 300 tokens) so that 100% of the context fits directly into downstream decision engines with zero truncation.

Structure your briefing with the following markdown headers:
## 1. Macro & Yield Trajectory
Summarize benchmark Treasury yields (10Y/2Y, TLT), inflation prints, and morning economic releases.

## 2. Multi-Day Trend & Overnight Tape
Report rolling 5-day SPY return, 20-day SMA distance, prior 3-day direction sequence, and SPY/QQQ pre-market gap percentages with breadth confirmation.

## 3. Options Derivatives & Positioning
Report Put/Call ratios, Max Pain levels, and gamma/volatility skew indications.

## 4. Institutional Consensus & Historical Lessons
Extract top macro themes and warnings from ingested newsletters, incorporating relevant historical lessons learned.

## 5. Directional Tension & Key Levels
Highlight symmetric upside triggers vs downside vulnerabilities heading into the 9:30 AM ET open bell.

IMPORTANT CONSTRAINTS:
- Do NOT generate your own UP/DOWN prediction. Provide pure, factual distillation for downstream decision engines.
- Be concise, objective, and dense. Avoid fluff, filler greetings, or conversational remarks.
"""


DEFAULT_CACHE_DB = ".local_autoresearch_cache.db"
MAX_INPUT_CHAR_CEILING = 180000


def decode_mime_header(header_text: str) -> str:
    """Safely decode MIME-encoded email headers like =?utf-8?B?...?="""
    if not header_text:
        return ""
    try:
        import email.header

        decoded_parts = email.header.decode_header(header_text)
        result: list[str] = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return "".join(result).strip()
    except Exception:
        return header_text.strip()


def clean_newsletter_text_locally(raw_text: str) -> str:
    """Deterministic local ad, tracking link, boilerplate, and HTML cleaner for financial newsletters."""
    if not raw_text:
        return ""

    import re

    text = raw_text

    # 1. Strip HTML tags like <style>, <script>, <img ...>, <a ...>, <div ...>
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)

    # 2. Strip markdown images and convert markdown links to plain text: [text](http...) -> text
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    # 3. Strip raw URLs and tracking tokens / JWTs
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"(?:jwt|token|id_token|utm_[a-z]+)=[A-Za-z0-9_.\-%]+", "", text, flags=re.IGNORECASE)

    # 4. Strip common sponsorship / header navigation fluff
    patterns_to_remove = [
        r"View\s+(?:in\s+browser|Online)\s*(?:\|\s*Sign\s*Up\s*\|\s*Shop)?",
        r"Presented\s+By\s*(?:Sponsor\s+Logo:?[^\n]*)?",
        r"Newsletter\s+Logo",
        r"Sponsor\s+Logo:?[^\n]*",
    ]
    for pat in patterns_to_remove:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE)

    # 5. Strip boilerplate unsubscribe / disclaimer footers at the end
    footer_markers = [
        r"(?:Unsubscribe\b|Update\s+your\s+email\s+preferences|To\s+stop\s+receiving\s+this\s+newsletter).*$",
        r"Copyright\s+.*?(?:All\s+rights\s+reserved).*$",
        r"ADVERTISE\s*//\s*CAREERS\s*//\s*SHOP\s*//\s*FAQ.*$",
        r"etoro\s+makes\s+no\s+representation\s+and\s+assumes\s+no\s+liability.*$",
    ]
    for fpat in footer_markers:
        text = re.sub(fpat, " ", text, flags=re.IGNORECASE | re.DOTALL)

    # 6. Collapse excessive whitespace and blank lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def get_rolling_trend_vector(target_date: str, db_path: str = DEFAULT_CACHE_DB) -> dict[str, Any]:
    """Compute rolling point-in-time trend vector strictly prior to target_date (zero lookahead)."""

    if not os.path.exists(db_path):
        return {"summary": "", "days_available": 0, "prior_date": None, "prior_close": None}

    try:
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT target_date, open_price, close_price, actual_direction
                FROM cached_days
                WHERE target_date < ?
                ORDER BY target_date DESC
                LIMIT 25
                """,
                (target_date,),
            )
            rows = cursor.fetchall()
    except Exception as e:
        logger.debug(f"Could not load rolling trend vector for {target_date}: {e}")
        return {"summary": "", "days_available": 0, "prior_date": None, "prior_close": None}

    if not rows:
        return {"summary": "", "days_available": 0, "prior_date": None, "prior_close": None}

    # Chronological order: oldest to newest
    chrono_rows = list(reversed(rows))
    prior_row = chrono_rows[-1]
    prior_date = prior_row[0]
    prior_close = float(prior_row[2])

    close_prices = [float(r[2]) for r in chrono_rows]

    # 5-day return %
    return_5d_pct: float | None = None
    if len(close_prices) >= 6:
        base_5d = close_prices[-6]
        if base_5d > 0:
            return_5d_pct = ((prior_close - base_5d) / base_5d) * 100.0
    elif len(close_prices) > 1 and close_prices[0] > 0:
        return_5d_pct = ((prior_close - close_prices[0]) / close_prices[0]) * 100.0

    # 20-day SMA distance %
    sma_20_dist_pct: float | None = None
    sma_len = min(len(close_prices), 20)
    if sma_len > 0:
        sma_val = sum(close_prices[-sma_len:]) / sma_len
        if sma_val > 0:
            sma_20_dist_pct = ((prior_close - sma_val) / sma_val) * 100.0

    # 3-day direction sequence
    recent_3 = chrono_rows[-3:] if len(chrono_rows) >= 3 else chrono_rows
    seq_items = []
    for r in recent_3:
        d_date, d_open, d_close, d_dir = r[0], float(r[1]), float(r[2]), r[3]
        chg = ((d_close - d_open) / d_open * 100.0) if d_open > 0 else 0.0
        seq_items.append(f"{d_date}: {d_dir} ({chg:+.2f}%)")
    seq_str = " -> ".join(seq_items)

    lines = [
        f"- Prior Session Close ({prior_date}): ${prior_close:.2f}",
        f"- 3-Day Direction Sequence: {seq_str}",
    ]
    if return_5d_pct is not None:
        lines.append(f"- Rolling 5-Day SPY Return: {return_5d_pct:+.2f}%")
    if sma_20_dist_pct is not None:
        lines.append(f"- 20-Day SMA Distance: {sma_20_dist_pct:+.2f}% (vs SMA{sma_len})")

    summary_str = "\n".join(lines)
    return {
        "summary": summary_str,
        "days_available": len(chrono_rows),
        "prior_date": prior_date,
        "prior_close": prior_close,
        "return_5d_pct": return_5d_pct,
        "sma_20_dist_pct": sma_20_dist_pct,
    }


def get_point_in_time_memories(
    target_date: str, db_path: str = DEFAULT_CACHE_DB, limit: int = 5
) -> list[dict[str, Any]]:
    """Retrieve top point-in-time lessons/memories created strictly prior to target_date (zero lookahead)."""

    if not os.path.exists(db_path):
        return []

    cutoff = f"{target_date}T00:00:00Z"
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT memory_type, content, importance_score, created_at
                FROM cached_memories
                WHERE created_at < ?
                ORDER BY importance_score DESC, created_at DESC
                LIMIT ?
                """,
                (cutoff, limit),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.debug(f"Could not load point-in-time memories for {target_date}: {e}")
        return []


def format_raw_point_in_time_inputs(day_record: dict[str, Any], db_path: str = DEFAULT_CACHE_DB) -> str:
    """Format raw daily observations into an uncompressed pre-market context block with zero lookahead."""
    target_date = day_record.get("target_date", "UNKNOWN_DATE")
    ticker = day_record.get("ticker", "SPY")
    lines: list[str] = [f"=== POINT-IN-TIME MARKET INPUTS: {ticker} ({target_date}) ==="]

    # 1. Multi-Day Momentum & Trend Vector (Zero lookahead)
    trend = get_rolling_trend_vector(target_date, db_path=db_path)
    if trend.get("summary"):
        lines.append("--- Multi-Day Momentum & Trend Vector ---")
        lines.append(trend["summary"].strip())

    # 2. Historical Memories & Lessons Learned (Strictly prior to target_date)
    memories = get_point_in_time_memories(target_date, db_path=db_path, limit=5)
    if memories:
        lines.append("--- Historical Lessons & Point-in-Time Memories ---")
        for mem in memories:
            m_type = mem.get("memory_type", "LESSON")
            m_content = mem.get("content", "").strip()
            lines.append(f"[{m_type}] {m_content}")

    # 3. Economic releases
    econ = day_record.get("economic_calendar")
    if econ:
        lines.append("--- High-Impact Economic Releases ---")
        lines.append(econ.strip())

    # 4. Benchmark Pre-Market Quotes & Proxies
    proxies_data = day_record.get("proxies", {})
    if proxies_data:
        lines.append("--- Benchmark Pre-Market Overnight Quotes ---")
        for sym in sorted(proxies_data.keys()):
            info = proxies_data.get(sym, {})
            p = info.get("price", 0.0)
            chg = info.get("change_pct", 0.0)
            lines.append(f"- {sym}: ${p:.2f} ({chg:+.2f}%)")

    # 5. Options Derivatives & Positioning
    options = day_record.get("options_sentiment")
    if options:
        lines.append("--- Options Derivatives & Positioning ---")
        lines.append(options.strip())

    # 6. Prior Session Intraday Profile
    profile = day_record.get("intraday_profile")
    if profile:
        lines.append("--- Prior Session Intraday Profile ---")
        lines.append(profile.strip())

    # 7. Ingested Newsletters (Full content with local de-ad/boilerplate cleaner, zero truncation)
    newsletters = day_record.get("newsletters", [])
    if newsletters:
        lines.append("--- Ingested Financial Newsletters ---")
        for item in newsletters:
            sender = item.get("sender", "Unknown")
            subject = decode_mime_header(item.get("subject", "No Subject"))
            raw_content = item.get("content", "")
            cleaned_content = clean_newsletter_text_locally(raw_content)
            if cleaned_content:
                lines.append(f"[{sender}] {subject}:\n{cleaned_content}\n")

    # 8. AI Synthetic Newsletter if present
    synth = day_record.get("synthetic_newsletter")
    if synth:
        lines.append("--- Synthetic Morning Summary ---")
        lines.append(synth.strip())

    lines.append("==================================================")
    full_text = "\n".join(lines)

    # Safety buffer ceiling: ensure input never exceeds 180,000 chars (~55,000 tokens)
    if len(full_text) > MAX_INPUT_CHAR_CEILING:
        trimmed_len = MAX_INPUT_CHAR_CEILING - 200
        warning_msg = (
            f"\n\n[INPUT EXCEEDED 180,000 CHAR SAFETY BUFFER: Truncated from {len(full_text)} to {MAX_INPUT_CHAR_CEILING} chars]"
            "\n=================================================="
        )
        full_text = full_text[:trimmed_len] + warning_msg

    return full_text


async def generate_daily_document(
    day_record: dict[str, Any],
    ingestion_prompt: str = DEFAULT_INGESTION_SYSTEM_PROMPT,
    base_url: str = DEFAULT_STRATA_URL,
    model_name: str = DEFAULT_STRATA_MODEL,
    client: httpx.AsyncClient | None = None,
    allow_fallback: bool = False,
    max_retries: int = 3,
    retry_delay_seconds: float = 5.0,
    db_path: str = DEFAULT_CACHE_DB,
) -> str:
    """Generate high-density daily market briefing document using local Qwen via Strata.

    Strictly local inference with zero external cloud API calls.
    Retries locally if Strata encounters transient engine reloads.
    Uses unconstrained max reasoning (reasoning_budget_tokens = -1).
    """
    if os.getenv("PYTEST_CURRENT_TEST") and retry_delay_seconds >= 1.0:
        retry_delay_seconds = 0.0

    raw_inputs = format_raw_point_in_time_inputs(day_record, db_path=db_path)
    user_prompt = (
        f"Please synthesize the following pre-market observations into a structured briefing document:\n\n{raw_inputs}"
    )

    headers = {"Content-Type": "application/json"}
    reasoning_budget = int(os.getenv("STRATA_REASONING_BUDGET_TOKENS", "-1"))
    max_tokens = int(os.getenv("STRATA_MAX_TOKENS", "8192"))
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": ingestion_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "reasoning_budget_tokens": reasoning_budget,
        "max_tokens": max_tokens,
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=180.0)
        should_close = True

    try:
        url = f"{base_url.rstrip('/')}/chat/completions"
        last_err: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise RuntimeError(f"Strata API returned HTTP {resp.status_code}: {resp.text}")

                raw_json = resp.json()
                data = await raw_json if hasattr(raw_json, "__await__") else raw_json
                msg = data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content") or msg.get("reasoning_content") or ""
                if not content.strip():
                    raise RuntimeError("Strata returned empty completion content")
                return content.strip()
            except Exception as strata_err:
                last_err = strata_err
                if attempt < max_retries:
                    wait_time = retry_delay_seconds * attempt
                    logger.warning(
                        f"Strata request failed ({strata_err}). Retrying locally {attempt}/{max_retries} in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Strata request failed after {max_retries} attempts: {strata_err}")

        raise RuntimeError(f"Strata document generation failed after {max_retries} attempts: {last_err}")
    finally:
        if should_close:
            await client.aclose()
