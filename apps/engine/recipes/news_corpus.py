"""Unified News Corpus module for the Voxel Strategy Recipe Studio.

Handles importing articles from stock-news-scraper shards, deriving canonical
thematic buckets, and running strict point-in-time queries without forward leakage.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from analysis.intraday_news_aggregator import aggregate_intraday_news
from core.config import ALPACA_API_KEY, ALPACA_SECRET_KEY, FMP_API_KEY, MASSIVE_API_KEY, logger

MACRO_INDEX_TICKERS = ["SPY", "QQQ", "TLT"]

# Precompiled regexes for bucket derivation
_BUCKET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "semiconductors",
        re.compile(r"\b(semiconductor|chips?|foundry|foundries|data\s*centers?|gpu|wafer|asml|tsmc)\b", re.I),
    ),
    ("ai_cloud", re.compile(r"\b(artificial\s*intelligence|\bai\b|cloud|hyperscalers?|llms?|generative\s*ai)\b", re.I)),
    (
        "earnings",
        re.compile(r"\b(earnings|quarterly|revenue|eps|guidance|beat|missed|fiscal\s*q[1-4]|q[1-4]\s*profit)\b", re.I),
    ),
    (
        "fed_rates",
        re.compile(
            r"\b(federal\s*reserve|\bfed\b|powell|rate\s*cuts?|rate\s*hikes?|fomc|interest\s*rates?|basis\s*points?)\b",
            re.I,
        ),
    ),
    ("macro_inflation", re.compile(r"\b(cpi|ppi|pce|inflation|payrolls?|unemployment|jobless\s*claims|gdp)\b", re.I)),
    ("energy", re.compile(r"\b(crude|oil|petroleum|opec|refinery|natural\s*gas|drilling)\b", re.I)),
    ("financials", re.compile(r"\b(investment\s*bank|lending|deposits?|credit\s*card|yield\s*curve|treasury)\b", re.I)),
    ("healthcare", re.compile(r"\b(fda|clinical\s*trials?|drug|pharmaceutical|biotech|vaccine|therapy)\b", re.I)),
    ("tariffs_trade", re.compile(r"\b(tariffs?|trade\s*war|export\s*controls?|sanctions?|protectionism)\b", re.I)),
    ("m_and_a", re.compile(r"\b(acquisition|acquired|merger|buyout|takeover|tender\s*offer)\b", re.I)),
]

_COMPANY_TO_BUCKETS: dict[str, list[str]] = {
    "Nvidia": ["semiconductors", "ai_cloud"],
    "AMD": ["semiconductors", "ai_cloud"],
    "Broadcom": ["semiconductors", "ai_cloud"],
    "Micron Technology": ["semiconductors"],
    "Applied Materials": ["semiconductors"],
    "Microsoft": ["ai_cloud"],
    "Alphabet": ["ai_cloud"],
    "Amazon": ["ai_cloud"],
    "Meta": ["ai_cloud"],
    "Oracle": ["ai_cloud"],
    "Exxon Mobil": ["energy"],
    "Chevron": ["energy"],
    "JPMorgan Chase": ["financials"],
    "Goldman Sachs": ["financials"],
    "Morgan Stanley": ["financials"],
    "Charles Schwab": ["financials"],
    "BlackRock": ["financials"],
    "Eli Lilly": ["healthcare"],
    "Johnson & Johnson": ["healthcare"],
    "Merck": ["healthcare"],
    "AbbVie": ["healthcare"],
    "Abbott Laboratories": ["healthcare"],
}


def derive_article_buckets(
    title: str,
    full_text: str,
    company: str = "",
    companies: list[str] | None = None,
    tickers: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Derive canonical thematic buckets and normalize macro tickers.

    Returns:
        (buckets_list, normalized_tickers_list)
    """
    buckets_set: set[str] = set()
    norm_tickers: list[str] = list(tickers or [])
    combined_text = f"{title}\n{full_text[:1500]}"

    # 1. Company mapping
    all_comps = [company] + (companies or [])
    for comp in all_comps:
        if comp in _COMPANY_TO_BUCKETS:
            buckets_set.update(_COMPANY_TO_BUCKETS[comp])

    # 2. General market macro logic
    is_general_market = company == "general_market" or not norm_tickers
    if is_general_market:
        buckets_set.add("macro_general")
        for macro_ticker in MACRO_INDEX_TICKERS:
            if macro_ticker not in norm_tickers:
                norm_tickers.append(macro_ticker)

    # 3. Regex keyword matching
    for b_name, b_re in _BUCKET_PATTERNS:
        if b_re.search(combined_text):
            buckets_set.add(b_name)

    if not buckets_set:
        buckets_set.add("general_market")

    return sorted(buckets_set), sorted(set(norm_tickers))


def parse_and_normalize_article(raw_record: dict[str, Any]) -> dict[str, Any] | None:
    """Parse raw JSONL record from stock-news-scraper into recipe_news_corpus schema."""
    article_id = raw_record.get("article_id")
    title = (raw_record.get("title") or "").strip()
    url = (raw_record.get("url") or "").strip()
    raw_date = raw_record.get("date_published")

    if not article_id or not title or not url or not raw_date:
        return None

    # Date normalization
    try:
        clean_date = raw_date.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        iso_published = dt.astimezone(UTC).isoformat()
    except Exception:
        return None

    full_text = (raw_record.get("full_text") or "").strip()
    word_count = raw_record.get("word_count") or len(full_text.split())
    company = (raw_record.get("company") or "general_market").strip()
    companies = raw_record.get("companies") or ([company] if company != "general_market" else [])
    raw_tickers = raw_record.get("tickers") or []

    buckets, normalized_tickers = derive_article_buckets(
        title=title,
        full_text=full_text,
        company=company,
        companies=companies,
        tickers=raw_tickers,
    )

    return {
        "article_id": str(article_id),
        "title": title,
        "url": url,
        "date_published": iso_published,
        "date_precision": raw_record.get("date_precision") or "article_meta",
        "source": raw_record.get("source") or "unknown",
        "source_family": raw_record.get("source_family") or "unknown",
        "full_text": full_text,
        "word_count": int(word_count),
        "company": company,
        "companies": companies,
        "tickers": normalized_tickers,
        "company_in_headline": bool(raw_record.get("company_in_headline", False)),
        "buckets": buckets,
    }


def import_stock_news_corpus(
    corpus_paths: list[str | Path],
    sb_client: Any,
    batch_size: int = 200,
) -> dict[str, int]:
    """Import JSONL records into public.recipe_news_corpus idempotently."""
    stats = {"total_read": 0, "inserted": 0, "skipped_or_invalid": 0}
    batch: list[dict[str, Any]] = []

    for path_item in corpus_paths:
        p = Path(path_item)
        if not p.exists():
            continue

        files = sorted(p.glob("*.jsonl")) if p.is_dir() else [p]
        for f in files:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    stats["total_read"] += 1
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        norm = parse_and_normalize_article(raw)
                        if not norm:
                            stats["skipped_or_invalid"] += 1
                            continue
                        batch.append(norm)
                    except Exception:
                        stats["skipped_or_invalid"] += 1
                        continue

                    if len(batch) >= batch_size:
                        try:
                            res = (
                                sb_client.table("recipe_news_corpus").upsert(batch, on_conflict="article_id").execute()
                            )
                            inserted_count = len(res.data) if getattr(res, "data", None) else len(batch)
                            stats["inserted"] += inserted_count
                        except Exception:
                            logger.exception("Error executing batch upsert to recipe_news_corpus")
                        batch = []

    if batch:
        try:
            res = sb_client.table("recipe_news_corpus").upsert(batch, on_conflict="article_id").execute()
            inserted_count = len(res.data) if getattr(res, "data", None) else len(batch)
            stats["inserted"] += inserted_count
        except Exception:
            logger.exception("Error executing final batch upsert to recipe_news_corpus")

    return stats


async def sync_live_news_to_corpus(
    sb_client: Any,
    *,
    as_of_utc: datetime | None = None,
    symbols: str = "SPY,QQQ,NVDA,AMD,AAPL,MSFT,AMZN,META,GOOGL,TSLA",
    lookback_hours: int = 48,
    batch_size: int = 50,
) -> dict[str, int]:
    """Sync live wire headlines and recent newsletter_snapshots into recipe_news_corpus."""
    now_utc = as_of_utc or datetime.now(UTC)
    floor_iso = (now_utc - timedelta(hours=max(1, lookback_hours))).isoformat()
    records: list[dict[str, Any]] = []

    try:
        wire_items = await aggregate_intraday_news(
            massive_api_key=MASSIVE_API_KEY or "",
            fmp_api_key=FMP_API_KEY or "",
            alpaca_api_key=ALPACA_API_KEY or "",
            alpaca_secret_key=ALPACA_SECRET_KEY or "",
            symbols=symbols,
            limit_per_source=25,
        )
        for item in wire_items:
            aid = str(item.get("source_id_hash") or "").strip()
            if not aid:
                continue
            tickers = [str(t).upper().strip() for t in (item.get("tickers") or []) if str(t).strip()]
            norm = parse_and_normalize_article(
                {
                    "article_id": aid,
                    "title": item.get("headline", ""),
                    "url": item.get("url") or f"https://benchify.app/news/{aid}",
                    "date_published": item.get("published_at") or now_utc.isoformat(),
                    "date_precision": "wire_timestamp",
                    "source": item.get("source") or "market_wire",
                    "source_family": "market_wire",
                    "full_text": item.get("summary") or item.get("headline", ""),
                    "company": tickers[0] if len(tickers) == 1 else "general_market",
                    "tickers": tickers,
                }
            )
            if norm:
                records.append(norm)
    except Exception:
        logger.exception("Failed fetching live wire news for recipe_news_corpus")

    try:
        snap_res = (
            sb_client.table("newsletter_snapshots")
            .select("source_id, sender, subject, content, date")
            .gte("date", floor_iso)
            .order("date", desc=True)
            .limit(50)
            .execute()
        )
        for snap in snap_res.data or []:
            src_id = str(snap.get("source_id") or "").strip()
            if not src_id:
                continue
            aid = f"nl_{src_id}"
            norm = parse_and_normalize_article(
                {
                    "article_id": aid,
                    "title": snap.get("subject") or snap.get("sender") or "Market Newsletter",
                    "url": f"https://benchify.app/newsletters/{src_id}",
                    "date_published": snap.get("date") or now_utc.isoformat(),
                    "date_precision": "newsletter_date",
                    "source": snap.get("sender") or "newsletter",
                    "source_family": "newsletter",
                    "full_text": snap.get("content") or "",
                    "company": "general_market",
                    "tickers": [],
                }
            )
            if norm:
                records.append(norm)
    except Exception:
        logger.exception("Failed fetching newsletter_snapshots for recipe_news_corpus")

    inserted = 0
    for i in range(0, len(records), batch_size):
        chunk = records[i : i + batch_size]
        try:
            res = sb_client.table("recipe_news_corpus").upsert(chunk, on_conflict="article_id").execute()
            inserted += len(res.data) if getattr(res, "data", None) else len(chunk)
        except Exception:
            logger.exception("Failed upserting live news batch into recipe_news_corpus")

    return {"fetched": len(records), "inserted": inserted}
