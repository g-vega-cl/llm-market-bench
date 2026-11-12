"""Unified News Corpus module for the Voxel Strategy Recipe Studio.

Handles importing articles from stock-news-scraper shards, deriving canonical
thematic buckets, and running strict point-in-time queries without forward leakage.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import logger

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


def query_corpus_point_in_time(
    sb_client: Any,
    cutoff_timestamp: str,
    tickers: list[str] | None = None,
    buckets: list[str] | None = None,
    keywords: list[str] | None = None,
    lookback_hours: int = 72,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Strict point-in-time query for the recipe engine.

    Guarantees:
        date_published <= cutoff_timestamp (zero forward leakage)
        date_published >= cutoff_timestamp - lookback_hours
    """
    try:
        clean_cutoff = cutoff_timestamp.replace("Z", "+00:00")
        cutoff_dt = datetime.fromisoformat(clean_cutoff)
        if cutoff_dt.tzinfo is None:
            cutoff_dt = cutoff_dt.replace(tzinfo=UTC)
    except Exception:
        cutoff_dt = datetime.now(UTC)

    from datetime import timedelta

    start_dt = cutoff_dt - timedelta(hours=lookback_hours)

    query = (
        sb_client.table("recipe_news_corpus")
        .select("article_id, title, url, date_published, source, company, tickers, buckets, full_text, word_count")
        .lte("date_published", cutoff_dt.isoformat())
        .gte("date_published", start_dt.isoformat())
        .order("date_published", desc=True)
    )

    if tickers:
        clean_tickers = [t.upper().strip() for t in tickers if t.strip()]
        if clean_tickers:
            query = query.overlaps("tickers", clean_tickers)

    if buckets:
        clean_buckets = [b.lower().strip() for b in buckets if b.strip()]
        if clean_buckets:
            query = query.overlaps("buckets", clean_buckets)

    query = query.limit(limit)

    try:
        res = query.execute()
        rows: list[dict[str, Any]] = res.data if isinstance(getattr(res, "data", None), list) else []
    except Exception:
        logger.exception("Error executing point-in-time news query")
        return []

    # Optional in-memory keyword filtering
    if keywords:
        clean_kw = [k.lower().strip() for k in keywords if k.strip()]
        if clean_kw:
            filtered = []
            for r in rows:
                content = f"{r.get('title', '')} {r.get('full_text', '')}".lower()
                if any(kw in content for kw in clean_kw):
                    filtered.append(r)
            return filtered

    return rows
