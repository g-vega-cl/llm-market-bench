"""Hermetic unit tests for ticker and sector mention extraction, alias resolution, and deduplication."""

from tasks.ticker_extractor import (
    extract_and_deduplicate_mentions,
    normalize_sector_to_etf,
    normalize_ticker,
)


def test_normalize_ticker():
    assert normalize_ticker(" $NVDA ") == "NVDA"
    assert normalize_ticker("aapl") == "AAPL"
    assert normalize_ticker("Google") == "GOOGL"
    assert normalize_ticker("Alphabet") == "GOOGL"
    assert normalize_ticker("Meta Platforms") == "META"
    assert normalize_ticker("BRK-B") == "BRK.B"
    assert normalize_ticker("UnknownXYZ123") == "UNKNOWNXYZ123"


def test_normalize_sector_to_etf():
    assert normalize_sector_to_etf("Semiconductors") == ("SMH", "VanEck Semiconductor ETF")
    assert normalize_sector_to_etf("Chips & Hardware") == ("SMH", "VanEck Semiconductor ETF")
    assert normalize_sector_to_etf("Cybersecurity") == ("CIBR", "First Trust NASDAQ Cybersecurity ETF")
    assert normalize_sector_to_etf("Software / SaaS") == ("IGV", "iShares Expanded Tech-Software Sector ETF")
    assert normalize_sector_to_etf("Energy & Oil") == ("XLE", "Energy Select Sector SPDR Fund")
    assert normalize_sector_to_etf("Biotechnology") == ("XBI", "SPDR S&P Biotech ETF")
    assert normalize_sector_to_etf("Financials") == ("XLF", "Financial Select Sector SPDR Fund")
    assert normalize_sector_to_etf("Random Niche") is None


def test_extract_and_deduplicate_mentions():
    raw_mentions = [
        {"ticker": "NVDA", "company_name": "NVIDIA", "sector": "Semiconductors"},
        {"ticker": "$nvda", "company_name": "Nvidia Corp", "sector": "Semis"},
        {"ticker": "NVIDIA", "company_name": "Nvidia", "sector": "Hardware"},
        {"ticker": "Google", "company_name": "Alphabet Inc", "sector": "Communication Services"},
        {"ticker": "GOOGL", "company_name": "Alphabet", "sector": "Tech"},
        {"ticker": "Semiconductors", "company_name": "Semis", "sector": "Semiconductors"},
        {"ticker": "Energy", "company_name": "Energy Sector", "sector": "Energy"},
    ]

    deduped = extract_and_deduplicate_mentions(raw_mentions)
    tickers = [m.ticker for m in deduped]

    # Should deduplicate NVDA (3 mentions -> 1)
    # Should deduplicate GOOGL / Google (2 mentions -> 1)
    # Should map Semiconductors to SMH
    # Should map Energy to XLE
    assert tickers == ["NVDA", "GOOGL", "SMH", "XLE"]

    smh = next(m for m in deduped if m.ticker == "SMH")
    assert smh.is_sector_etf is True
    assert smh.entity_type == "etf"

    nvda = next(m for m in deduped if m.ticker == "NVDA")
    assert nvda.is_sector_etf is False
    assert nvda.entity_type == "stock"


def test_extract_from_text_fallback():
    sample_text = (
        "In tech, Apple (AAPL) showed resilience while Microsoft ($MSFT) gained. "
        "The Semiconductor sector rallied behind NVIDIA ($NVDA). "
        "Cybersecurity stocks also surged."
    )
    mentions = extract_and_deduplicate_mentions(raw_items=[], text_fallback=sample_text)
    tickers = [m.ticker for m in mentions]

    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert "NVDA" in tickers
    assert "SMH" in tickers
    assert "CIBR" in tickers


def test_extract_rejects_financial_acronyms_and_accidental_substrings():
    sample_text = (
        "Operating earnings per share (EPS) surged 25% year-over-year (YOY). "
        "The market multiple (PE) expanded above 20x, boosting enterprise value (EV). "
        "Central bank policy remains accommodative for blue-chip companies with large addressable markets (TAM)."
    )
    mentions = extract_and_deduplicate_mentions(raw_items=[], text_fallback=sample_text)
    tickers = [m.ticker for m in mentions]

    # Verify none of the financial acronyms or accidental substrings ("blue-chip", "central bank") became tickers
    assert "EPS" not in tickers
    assert "YOY" not in tickers
    assert "PE" not in tickers
    assert "EV" not in tickers
    assert "TAM" not in tickers
    assert "SMH" not in tickers
    assert "XLF" not in tickers
    assert len(tickers) == 0
