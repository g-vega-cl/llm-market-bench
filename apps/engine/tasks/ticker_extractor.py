"""Ticker and sector extraction, canonical alias normalization, and deduplication utility."""

import re
from typing import Any

from pydantic import BaseModel, Field

# Common company alias resolution to standard ticker symbol
ALIAS_MAP: dict[str, str] = {
    "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "NVIDIA": "NVDA",
    "TESLA": "TSLA",
    "AMAZON": "AMZN",
    "META": "META",
    "META PLATFORMS": "META",
    "FACEBOOK": "META",
    "BERKSHIRE": "BRK.B",
    "BERKSHIRE HATHAWAY": "BRK.B",
    "NETFLIX": "NFLX",
    "TAIWAN SEMICONDUCTOR": "TSM",
    "TSMC": "TSM",
    "BROADCOM": "AVGO",
    "ADVANCED MICRO DEVICES": "AMD",
    "PALANTIR": "PLTR",
}

FINANCIAL_ACRONYM_BLACKLIST: set[str] = {
    "USD",
    "CEO",
    "CFO",
    "COO",
    "CTO",
    "AI",
    "GDP",
    "CPI",
    "PPI",
    "SEC",
    "FED",
    "EPS",
    "PE",
    "EV",
    "ARR",
    "CAGR",
    "FCF",
    "TAM",
    "IPO",
    "YOY",
    "QOQ",
    "MOM",
    "FOMC",
    "VIX",
    "ETF",
    "NAV",
    "ROIC",
    "ROE",
    "ROA",
    "EBITDA",
    "EBIT",
    "GAAP",
    "DXY",
    "FX",
    "PMI",
    "ISM",
    "BLS",
    "SPX",
    "NDX",
    "DJIA",
    "ATH",
    "YTD",
    "LTM",
    "NTM",
}

# Explicit sector phrases to avoid accidental substrings like 'blue-chip' or 'central bank'
SECTOR_TEXT_PATTERNS: dict[str, tuple[str, str]] = {
    r"\bsemiconductors?\b": ("SMH", "VanEck Semiconductor ETF"),
    r"\bcybersecurity\b": ("CIBR", "First Trust NASDAQ Cybersecurity ETF"),
    r"\bsoftware sector\b": ("IGV", "iShares Expanded Tech-Software Sector ETF"),
    r"\bcloud software\b": ("IGV", "iShares Expanded Tech-Software Sector ETF"),
    r"\benergy sector\b": ("XLE", "Energy Select Sector SPDR Fund"),
    r"\boil & gas\b": ("XLE", "Energy Select Sector SPDR Fund"),
    r"\bfinancial sector\b": ("XLF", "Financial Select Sector SPDR Fund"),
    r"\bbiotechnology\b": ("XBI", "SPDR S&P Biotech ETF"),
    r"\bbiotech sector\b": ("XBI", "SPDR S&P Biotech ETF"),
    r"\butilities sector\b": ("XLU", "Utilities Select Sector SPDR Fund"),
    r"\bindustrials sector\b": ("XLI", "Industrial Select Sector SPDR Fund"),
    r"\breal estate sector\b": ("XLRE", "Real Estate Select Sector SPDR Fund"),
    r"\bdefense sector\b": ("ITA", "iShares U.S. Aerospace & Defense ETF"),
}
SECTOR_ETF_MAP: dict[str, tuple[str, str]] = {
    "SEMICONDUCTOR": ("SMH", "VanEck Semiconductor ETF"),
    "CHIP": ("SMH", "VanEck Semiconductor ETF"),
    "SEMI": ("SMH", "VanEck Semiconductor ETF"),
    "CYBERSECURITY": ("CIBR", "First Trust NASDAQ Cybersecurity ETF"),
    "CYBER": ("CIBR", "First Trust NASDAQ Cybersecurity ETF"),
    "SOFTWARE": ("IGV", "iShares Expanded Tech-Software Sector ETF"),
    "SAAS": ("IGV", "iShares Expanded Tech-Software Sector ETF"),
    "CLOUD": ("IGV", "iShares Expanded Tech-Software Sector ETF"),
    "ENERGY": ("XLE", "Energy Select Sector SPDR Fund"),
    "OIL": ("XLE", "Energy Select Sector SPDR Fund"),
    "FINANCIAL": ("XLF", "Financial Select Sector SPDR Fund"),
    "BANK": ("XLF", "Financial Select Sector SPDR Fund"),
    "BIOTECH": ("XBI", "SPDR S&P Biotech ETF"),
    "PHARMA": ("XBI", "SPDR S&P Biotech ETF"),
    "UTILITIES": ("XLU", "Utilities Select Sector SPDR Fund"),
    "INDUSTRIAL": ("XLI", "Industrial Select Sector SPDR Fund"),
    "REAL ESTATE": ("XLRE", "Real Estate Select Sector SPDR Fund"),
    "REIT": ("XLRE", "Real Estate Select Sector SPDR Fund"),
    "DISCRETIONARY": ("XLY", "Consumer Discretionary Select Sector SPDR Fund"),
    "RETAIL": ("XLY", "Consumer Discretionary Select Sector SPDR Fund"),
    "STAPLES": ("XLP", "Consumer Staples Select Sector SPDR Fund"),
    "COMMUNICATION": ("XLC", "Communication Services Select Sector SPDR Fund"),
    "AEROSPACE": ("ITA", "iShares U.S. Aerospace & Defense ETF"),
    "DEFENSE": ("ITA", "iShares U.S. Aerospace & Defense ETF"),
}


class CompanyMention(BaseModel):
    """Normalized structured company or sector target."""

    ticker: str = Field(description="Normalized ticker symbol or ETF ticker (e.g. NVDA, SMH).")
    company_name: str = Field(description="Company or ETF name.")
    sector: str | None = Field(default=None, description="Industry or sector name.")
    is_sector_etf: bool = Field(default=False, description="True if this is a sector proxy ETF.")
    entity_type: str = Field(default="stock", description="'stock' or 'etf'.")
    context_snippet: str | None = Field(default=None, description="Newsletter context mentioning this target.")


def normalize_ticker(raw_ticker: str) -> str:
    """Normalize raw ticker string: strip whitespace, dollar signs, and resolve aliases."""
    if not raw_ticker:
        return ""
    clean = raw_ticker.strip().lstrip("$").upper().replace("-", ".")
    return ALIAS_MAP.get(clean, clean)


def normalize_sector_to_etf(sector_text: str) -> tuple[str, str] | None:
    """Match sector phrases to a canonical benchmark ETF (ticker, ETF name)."""
    if not sector_text:
        return None
    upper = sector_text.upper()
    for keyword, etf_info in SECTOR_ETF_MAP.items():
        if keyword in upper:
            return etf_info
    return None


def extract_and_deduplicate_mentions(
    raw_items: list[dict[str, Any]],
    text_fallback: str | None = None,
) -> list[CompanyMention]:
    """Extract, normalize, map sectors to ETFs, and deduplicate company/sector mentions.

    Guarantees each target symbol appears at most once in the resulting list.
    """
    seen_tickers: set[str] = set()
    result: list[CompanyMention] = []

    def _add_target(
        ticker: str,
        name: str,
        sector: str | None,
        is_etf: bool,
        snippet: str | None,
    ):
        norm_sym = normalize_ticker(ticker)
        # Check if the ticker itself is a sector name
        etf_match = normalize_sector_to_etf(norm_sym)
        if etf_match:
            norm_sym = etf_match[0]
            name = etf_match[1]
            is_etf = True

        if not norm_sym or norm_sym in seen_tickers:
            return

        seen_tickers.add(norm_sym)
        result.append(
            CompanyMention(
                ticker=norm_sym,
                company_name=name or norm_sym,
                sector=sector,
                is_sector_etf=is_etf,
                entity_type="etf" if is_etf else "stock",
                context_snippet=snippet,
            )
        )

    # 1. Process explicit structured raw items
    for item in raw_items:
        raw_tick = item.get("ticker") or ""
        raw_name = item.get("company_name") or raw_tick
        raw_sector = item.get("sector")
        snippet = item.get("context_snippet")

        # Check if the item is explicitly a sector
        etf_match = normalize_sector_to_etf(raw_tick) or (
            normalize_sector_to_etf(raw_sector) if raw_tick.upper() in ["SECTOR", "ETF", "INDUSTRY"] else None
        )

        if etf_match:
            _add_target(etf_match[0], etf_match[1], raw_sector or raw_tick, True, snippet)
        else:
            _add_target(raw_tick, raw_name, raw_sector, False, snippet)

    # 2. If text fallback provided, scan for cashtags ($XYZ), named parentheticals, and explicit sectors
    if text_fallback:
        # Match cash tags: $XYZ
        dollar_tickers = re.findall(r"\$([A-Z]{1,5})\b", text_fallback)
        for sym in dollar_tickers:
            if sym not in FINANCIAL_ACRONYM_BLACKLIST:
                _add_target(sym, sym, None, False, None)

        # Match named company parentheticals: e.g. "Apple (AAPL)", "Alphabet (GOOGL)"
        named_parens = re.findall(r"\b([A-Z][a-zA-Z0-9\s]{2,20})\s+\(([A-Z]{1,5})\)", text_fallback)
        for company_label, sym in named_parens:
            if sym not in FINANCIAL_ACRONYM_BLACKLIST:
                _add_target(sym, company_label.strip(), None, False, None)

        # Scan text for explicit sector phrases only
        for pattern, etf_info in SECTOR_TEXT_PATTERNS.items():
            if re.search(pattern, text_fallback, re.IGNORECASE):
                _add_target(etf_info[0], etf_info[1], etf_info[1].split()[0], True, None)

    return result
