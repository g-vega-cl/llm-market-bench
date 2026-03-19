# Financial Modeling Prep (FMP) API Documentation

## Overview

FMP (Financial Modeling Prep) is a comprehensive stock market API and financial data API provider offering real-time stock prices, financial statements, historical data, and more. The platform provides free stock market data, including audited, standardized, and real-time updates of income statements, balance sheets, and cash flow statements on a quarterly and annual basis.

## Authorization

All API requests must be authorized using an API key. Authorization can be done using either:

### Header Authorization
Include your API key in the request header:
```
apikey: YOUR_API_KEY
```

### URL Query Authorization
Append `?apikey=YOUR_API_KEY` at the end of every request.

**Note:** When adding the API key to your requests, ensure to use `&apikey=` if other query parameters already exist in the endpoint.

**Base URL:** `https://financialmodelingprep.com/stable/`

---

## Table of Contents

1. [Company Search](#company-search)
2. [Stock Directory](#stock-directory)
3. [Company Information](#company-information)
4. [Quote](#quote)
5. [Statements](#statements)
6. [Charts](#charts)
7. [Economics](#economics)
8. [Earnings, Dividends, Splits](#earnings-dividends-splits)
9. [Earnings Transcript](#earnings-transcript)
10. [News](#news)
11. [Form 13F](#form-13f)
12. [Analyst](#analyst)
13. [Market Performance](#market-performance)
14. [Technical Indicators](#technical-indicators)
15. [ETF and Mutual Funds](#etf-and-mutual-funds)
16. [SEC Filings](#sec-filings)
17. [Insider Trades](#insider-trades)
18. [Indexes](#indexes)
19. [Market Hours](#market-hours)
20. [Commodity](#commodity)
21. [Discounted Cash Flow](#discounted-cash-flow)
22. [Forex](#forex)
23. [Crypto](#crypto)
24. [Senate](#senate)
25. [ESG](#esg)
26. [Commitment Of Traders](#commitment-of-traders)
27. [Fundraisers](#fundraisers)
28. [Bulk](#bulk)

---

## Company Search

### Stock Symbol Search API
Easily find the ticker symbol of any stock. Search by symbol across multiple global markets.

**Endpoint:** `https://financialmodelingprep.com/stable/search-symbol?query=AAPL`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| query     | Yes      | string | AAPL       |
| limit     | No       | number | 50         |
| exchange  | No       | string | NASDAQ     |

**Response:**
```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "currency": "USD",
    "exchangeFullName": "NASDAQ Global Select",
    "exchange": "NASDAQ"
  }
]
```

### Company Name Search API
Search for ticker symbols, company names, and exchange details for equity securities and ETFs.

**Endpoint:** `https://financialmodelingprep.com/stable/search-name?query=AA`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| query     | Yes      | string | AA         |
| limit     | No       | number | 50         |
| exchange  | No       | string | NASDAQ     |

### CIK API
Retrieve the Central Index Key (CIK) for publicly traded companies.

**Endpoint:** `https://financialmodelingprep.com/stable/search-cik?cik=320193`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| cik       | Yes      | string | 320193     |
| limit     | No       | number | 50         |

### CUSIP API
Search and retrieve financial securities information by CUSIP number.

**Endpoint:** `https://financialmodelingprep.com/stable/search-cusip?cusip=037833100`

| Parameter | Required | Type   | Example       |
|-----------|----------|--------|---------------|
| cusip     | Yes      | string | 037833100     |

### ISIN API
Search and retrieve the International Securities Identification Number (ISIN).

**Endpoint:** `https://financialmodelingprep.com/stable/search-isin?isin=US0378331005`

| Parameter | Required | Type   | Example           |
|-----------|----------|--------|-------------------|
| isin      | Yes      | string | US0378331005      |

### Stock Screener API
Filter stocks based on market cap, price, volume, beta, sector, country, and more.

**Endpoint:** `https://financialmodelingprep.com/stable/company-screener`

| Parameter            | Type    | Example                    |
|----------------------|---------|----------------------------|
| marketCapMoreThan    | number  | 1000000                    |
| marketCapLowerThan   | number  | 1000000000                 |
| sector               | string  | Technology                 |
| industry             | string  | Consumer Electronics       |
| betaMoreThan         | number  | 0.5                        |
| betaLowerThan        | number  | 1.5                        |
| priceMoreThan        | number  | 10                         |
| priceLowerThan       | number  | 200                        |
| dividendMoreThan     | number  | 0.5                        |
| dividendLowerThan    | number  | 2                          |
| volumeMoreThan       | number  | 1000                       |
| volumeLowerThan      | number  | 1000000                    |
| exchange             | string  | NASDAQ                     |
| country              | string  | US                         |
| isEtf                | boolean | false                      |
| isFund               | boolean | false                      |
| isActivelyTrading    | boolean | true                       |
| limit                | number  | 1000                       |
| includeAllShareClasses | boolean | false                    |

### Exchange Variants API
Search across multiple public exchanges to find where a given stock symbol is listed.

**Endpoint:** `https://financialmodelingprep.com/stable/search-exchange-variants?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

---

## Stock Directory

### Company Symbols List API
Retrieve a comprehensive list of financial symbols from various global exchanges.

**Endpoint:** `https://financialmodelingprep.com/stable/stock-list`

### Financial Statement Symbols List API
Access a comprehensive list of companies with available financial statements.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-statement-symbol-list`

### CIK List API
Access a comprehensive database of CIK numbers for SEC-registered entities.

**Endpoint:** `https://financialmodelingprep.com/stable/cik-list?page=0&limit=1000`

### Symbol Changes List API
Track changes due to mergers, acquisitions, stock splits, and name changes.

**Endpoint:** `https://financialmodelingprep.com/stable/symbol-change`

### ETF Symbol Search API
Find ticker symbols and company names for Exchange Traded Funds (ETFs).

**Endpoint:** `https://financialmodelingprep.com/stable/etf-list`

### Actively Trading List API
List all actively trading companies and financial instruments.

**Endpoint:** `https://financialmodelingprep.com/stable/actively-trading-list`

### Earnings Transcript List API
Retrieve a list of companies with earnings transcripts.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings-transcript-list`

### Available Exchanges API
Access a complete list of supported stock exchanges.

**Endpoint:** `https://financialmodelingprep.com/stable/available-exchanges`

### Available Sectors API
Access a complete list of industry sectors.

**Endpoint:** `https://financialmodelingprep.com/stable/available-sectors`

### Available Industries API
Access a comprehensive list of industries where stock symbols are available.

**Endpoint:** `https://financialmodelingprep.com/stable/available-industries`

### Available Countries API
Access a comprehensive list of countries where stock symbols are available.

**Endpoint:** `https://financialmodelingprep.com/stable/available-countries`

---

## Company Information

### Company Profile Data API
Access detailed company profile data including market capitalization, stock price, industry, and more.

**Endpoint:** `https://financialmodelingprep.com/stable/profile?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Company Profile by CIK API
Retrieve detailed company profile data by CIK (Central Index Key).

**Endpoint:** `https://financialmodelingprep.com/stable/profile-cik?cik=320193`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| cik       | Yes      | string | 320193  |

### Company Notes API
Retrieve detailed information about company-issued notes.

**Endpoint:** `https://financialmodelingprep.com/stable/company-notes?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Stock Peer Comparison API
Identify and compare companies within the same sector and market capitalization range.

**Endpoint:** `https://financialmodelingprep.com/stable/stock-peers?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Delisted Companies API
Access a comprehensive list of companies that have been delisted from US exchanges.

**Endpoint:** `https://financialmodelingprep.com/stable/delisted-companies?page=0&limit=100`

### Company Employee Count API
Retrieve detailed workforce information including employee count, reporting period, and filing date.

**Endpoint:** `https://financialmodelingprep.com/stable/employee-count?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Company Historical Employee Count API
Access historical employee count data for a company based on specific reporting periods.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-employee-count?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Company Market Cap API
Retrieve the market capitalization for a specific company on any given date.

**Endpoint:** `https://financialmodelingprep.com/stable/market-capitalization?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Batch Market Cap API
Retrieve market capitalization data for multiple companies in a single request.

**Endpoint:** `https://financialmodelingprep.com/stable/market-capitalization-batch?symbols=AAPL,MSFT,GOOG`

| Parameter | Required | Type   | Example          |
|-----------|----------|--------|------------------|
| symbols   | Yes      | string | AAPL,MSFT,GOOG   |

### Historical Market Cap API
Access historical market capitalization data for a company.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-market-capitalization?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Company Share Float & Liquidity API
Access the total number of publicly traded shares for any company.

**Endpoint:** `https://financialmodelingprep.com/stable/shares-float?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### All Shares Float API
Access comprehensive shares float data for all available companies.

**Endpoint:** `https://financialmodelingprep.com/stable/shares-float-all?page=0&limit=1000`

### Latest Mergers & Acquisitions API
Access real-time data on the latest mergers and acquisitions.

**Endpoint:** `https://financialmodelingprep.com/stable/mergers-acquisitions-latest?page=0&limit=100`

### Search Mergers & Acquisitions API
Search for specific mergers and acquisitions data.

**Endpoint:** `https://financialmodelingprep.com/stable/mergers-acquisitions-search?name=Apple`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| name      | Yes      | string | Apple   |

### Company Executives API
Retrieve detailed information on company executives.

**Endpoint:** `https://financialmodelingprep.com/stable/key-executives?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Executive Compensation API
Retrieve comprehensive compensation data for company executives.

**Endpoint:** `https://financialmodelingprep.com/stable/governance-executive-compensation?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Executive Compensation Benchmark API
Gain access to average executive compensation data across various industries.

**Endpoint:** `https://financialmodelingprep.com/stable/executive-compensation-benchmark`

---

## Quote

### Stock Quote API
Access real-time stock quotes. Get up-to-the-minute prices, changes, and volume data.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Stock Quote Short API
Get quick snapshots of real-time stock quotes.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Aftermarket Trade API
Track real-time trading activity occurring after regular market hours.

**Endpoint:** `https://financialmodelingprep.com/stable/aftermarket-trade?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Aftermarket Quote API
Access real-time aftermarket quotes for stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/aftermarket-quote?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Stock Price Change API
Track stock price fluctuations in real-time over various time periods.

**Endpoint:** `https://financialmodelingprep.com/stable/stock-price-change?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Stock Batch Quote API
Retrieve multiple real-time stock quotes in a single request.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-quote?symbols=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbols   | Yes      | string | AAPL    |

### Stock Batch Quote Short API
Access real-time, short-form quotes for multiple stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-quote-short?symbols=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbols   | Yes      | string | AAPL    |

### Batch Aftermarket Trade API
Retrieve real-time aftermarket trading data for multiple stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-aftermarket-trade?symbols=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbols   | Yes      | string | AAPL    |

### Batch Aftermarket Quote API
Retrieve real-time aftermarket quotes for multiple stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-aftermarket-quote?symbols=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbols   | Yes      | string | AAPL    |

### Exchange Stock Quotes API
Retrieve real-time stock quotes for all listed stocks on a specific exchange.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-exchange-quote?exchange=NASDAQ`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| exchange  | Yes      | string | NASDAQ   |

### Mutual Fund Price Quotes API
Access real-time quotes for mutual funds.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-mutualfund-quotes`

### ETF Price Quotes API
Get real-time price quotes for exchange-traded funds (ETFs).

**Endpoint:** `https://financialmodelingprep.com/stable/batch-etf-quotes`

### Full Commodities Quotes API
Get up-to-the-minute quotes for commodities.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-commodity-quotes`

### Full Cryptocurrency Quotes API
Access real-time cryptocurrency quotes.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-crypto-quotes`

### Full Forex Quote API
Retrieve real-time quotes for multiple forex currency pairs.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-forex-quotes`

### Full Index Quotes API
Track real-time movements of major stock market indexes.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-index-quotes`

---

## Statements

### Income Statement API
Access detailed income statement data for publicly traded companies.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Balance Sheet Statement API
Access detailed balance sheet statements for publicly traded companies.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Cash Flow Statement API
Gain insights into a company's cash flow activities.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Latest Financial Statements API

**Endpoint:** `https://financialmodelingprep.com/stable/latest-financial-statements?page=0&limit=250`

### Income Statements TTM API

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-ttm?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Balance Sheet Statements TTM API

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-ttm?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Cashflow Statements TTM API

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-ttm?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Key Metrics API
Access essential financial metrics for a company.

**Endpoint:** `https://financialmodelingprep.com/stable/key-metrics?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Financial Ratios API
Analyze a company's financial performance using detailed profitability, liquidity, and efficiency ratios.

**Endpoint:** `https://financialmodelingprep.com/stable/ratios?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Key Metrics TTM API
Retrieve a comprehensive set of trailing twelve-month (TTM) key performance metrics.

**Endpoint:** `https://financialmodelingprep.com/stable/key-metrics-ttm?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Financial Ratios TTM API
Gain access to trailing twelve-month (TTM) financial ratios.

**Endpoint:** `https://financialmodelingprep.com/stable/ratios-ttm?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Financial Scores API
Assess a company's financial strength using metrics such as Altman Z-Score and Piotroski Score.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-scores?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Owner Earnings API
Retrieve a company's owner earnings.

**Endpoint:** `https://financialmodelingprep.com/stable/owner-earnings?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Enterprise Values API
Access a company's enterprise value.

**Endpoint:** `https://financialmodelingprep.com/stable/enterprise-values?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Income Statement Growth API
Track key financial growth metrics.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-growth?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Balance Sheet Statement Growth API
Analyze the growth of key balance sheet items over time.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-growth?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Cashflow Statement Growth API
Measure the growth rate of a company's cash flow.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-growth?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Financial Statement Growth API
Analyze the growth of key financial statement items across income, balance sheet, and cash flow statements.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-growth?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Financial Reports Dates API

**Endpoint:** `https://financialmodelingprep.com/stable/financial-reports-dates?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Financial Reports Form 10-K JSON API
Access comprehensive annual reports.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-reports-json?symbol=AAPL&year=2022&period=FY`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| year      | Yes      | string | 2022    |
| period    | Yes      | string | FY      |

### Financial Reports Form 10-K XLSX API
Download detailed 10-K reports in XLSX format.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-reports-xlsx?symbol=AAPL&year=2022&period=FY`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| year      | Yes      | string | 2022    |
| period    | Yes      | string | FY      |

### Revenue Product Segmentation API
Access detailed revenue breakdowns by product line.

**Endpoint:** `https://financialmodelingprep.com/stable/revenue-product-segmentation?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Revenue Geographic Segments API
Access detailed revenue breakdowns by geographic region.

**Endpoint:** `https://financialmodelingprep.com/stable/revenue-geographic-segmentation?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### As Reported Income Statements API
Retrieve income statements as they were reported by the company.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-as-reported?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### As Reported Balance Statements API
Access balance sheets as reported by the company.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-as-reported?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### As Reported Cashflow Statements API
View cash flow statements as reported by the company.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-as-reported?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### As Reported Financial Statements API
Retrieve comprehensive financial statements as reported by companies.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-statement-full-as-reported?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

---

## Charts

### Stock Chart Light API
Access simplified stock chart data including date, price, and trading volume.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Stock Price and Volume Data API
Access full price and volume data for any stock symbol.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Unadjusted Stock Price API
Access stock price and volume data without adjustments for stock splits.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/non-split-adjusted?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Dividend Adjusted Price Chart API
Analyze stock performance with dividend adjustments.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/dividend-adjusted?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### 1 Min Interval Stock Chart API
Access precise intraday stock price and volume data in 1-minute intervals.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### 5 Min Interval Stock Chart API
Access stock price and volume data in 5-minute intervals.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### 15 Min Interval Stock Chart API
Access stock price and volume data in 15-minute intervals.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/15min?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### 30 Min Interval Stock Chart API
Access stock price and volume data in 30-minute intervals.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/30min?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### 1 Hour Interval Stock Chart API
Track stock price movements over hourly intervals.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### 4 Hour Interval Stock Chart API
Analyze stock price movements over extended intraday periods.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/4hour?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

---

## Economics

### Treasury Rates API
Access latest and historical Treasury rates for all maturities.

**Endpoint:** `https://financialmodelingprep.com/stable/treasury-rates`

| Parameter | Required | Type | Example    |
|-----------|----------|------|------------|
| from      | Yes*     | date | 2025-09-09 |
| to        | Yes*     | date | 2025-12-09 |

*Max 90-day date range

**Response:**
```json
[
  {
    "date": "2024-02-29",
    "month1": 5.53,
    "month2": 5.5,
    "month3": 5.45,
    "month6": 5.3,
    "year1": 5.01,
    "year2": 4.64,
    "year3": 4.43,
    "year5": 4.26,
    "year7": 4.28,
    "year10": 4.25,
    "year20": 4.51,
    "year30": 4.38
  }
]
```

### Economics Indicators API
Access real-time and historical economic data for key indicators like GDP, unemployment, and inflation.

**Endpoint:** `https://financialmodelingprep.com/stable/economic-indicators?name=GDP`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| name      | Yes      | string | GDP     |
| from      | Yes*     | date   | 2024-12-09 |
| to        | Yes*     | date   | 2025-12-09 |

*Max 90-day date range

**Available indicators:** GDP, realGDP, nominalPotentialGDP, realGDPPerCapita, federalFunds, CPI, inflationRate, inflation, retailSales, consumerSentiment, durableGoods, unemploymentRate, totalNonfarmPayroll, initialClaims, industrialProductionTotalIndex, newPrivatelyOwnedHousingUnitsStartedTotalUnits, totalVehicleSales, retailMoneyFunds, smoothedUSRecessionProbabilities, 3MonthOr90DayRatesAndYieldsCertificatesOfDeposit, commercialBankInterestRateOnCreditCardPlansAllAccounts, 30YearFixedRateMortgageAverage, 15YearFixedRateMortgageAverage, tradeBalanceGoodsAndServices

**Response:**
```json
[
  {
    "name": "GDP",
    "date": "2024-01-01",
    "value": 28624.069
  }
]
```

### Economic Data Releases Calendar API
Access a comprehensive calendar of upcoming economic data releases.

**Endpoint:** `https://financialmodelingprep.com/stable/economic-calendar`

| Parameter | Required | Type | Example    |
|-----------|----------|------|------------|
| from      | Yes*     | date | 2025-09-09 |
| to        | Yes*     | date | 2025-12-09 |

*Max 90-day date range

### Market Risk Premium API
Access the market risk premium for specific dates.

**Endpoint:** `https://financialmodelingprep.com/stable/market-risk-premium`

---

## Earnings, Dividends, Splits

### Dividends Company API
Access essential dividend data for individual stock symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/dividends?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| limit     | No       | number | 100     |

*Maximum 1000 records per request*

**Response:**
```json
[
  {
    "symbol": "AAPL",
    "date": "2025-02-10",
    "recordDate": "2025-02-10",
    "paymentDate": "2025-02-13",
    "declarationDate": "2025-01-30",
    "adjDividend": 0.25,
    "dividend": 0.25,
    "yield": 0.42955326460481097,
    "frequency": "Quarterly"
  }
]
```

### Dividends Calendar API
Access a comprehensive schedule of dividend-related dates for all stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/dividends-calendar`

| Parameter | Required | Type | Example    |
|-----------|----------|------|------------|
| from      | Yes*     | date | 2025-09-09 |
| to        | Yes*     | date | 2025-12-09 |

*Maximum 4000 records per request, Max 90-day date range*

### Earnings Report API
Retrieve in-depth earnings information including EPS estimates and revenue projections.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| limit     | No       | number | 100     |

*Maximum 1000 records per request*

### Earnings Calendar API
Access key data including announcement dates, estimated EPS, and actual EPS.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings-calendar`

| Parameter | Required | Type | Example    |
|-----------|----------|------|------------|
| from      | Yes*     | date | 2025-09-09 |
| to        | Yes*     | date | 2025-12-09 |

*Maximum 4000 records per request, Max 90-day date range*

### IPOs Calendar API
Access a comprehensive list of all upcoming initial public offerings (IPOs).

**Endpoint:** `https://financialmodelingprep.com/stable/ipos-calendar`

| Parameter | Required | Type | Example    |
|-----------|----------|------|------------|
| from      | Yes*     | date | 2025-09-09 |
| to        | Yes*     | date | 2025-12-09 |

*Max 90-day date range*

### IPOs Disclosure API
Access a comprehensive list of disclosure filings for upcoming IPOs.

**Endpoint:** `https://financialmodelingprep.com/stable/ipos-disclosure`

| Parameter | Required | Type | Example    |
|-----------|----------|------|------------|
| from      | Yes      | date | 2025-09-09 |
| to        | Yes      | date | 2025-12-09 |

### IPOs Prospectus API
Access comprehensive information on IPO prospectuses.

**Endpoint:** `https://financialmodelingprep.com/stable/ipos-prospectus`

| Parameter | Required | Type | Example    |
|-----------|----------|------|------------|
| from      | Yes      | date | 2025-09-09 |
| to        | Yes      | date | 2025-12-09 |

### Stock Split Details API
Access detailed information on stock splits for a specific company.

**Endpoint:** `https://financialmodelingprep.com/stable/splits?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| limit     | No       | number | 100     |

*Maximum 1000 records per request*

### Stock Splits Calendar API
Access essential data on upcoming stock splits across multiple companies.

**Endpoint:** `https://financialmodelingprep.com/stable/splits-calendar`

| Parameter | Required | Type | Example    |
|-----------|----------|------|------------|
| from      | Yes*     | date | 2025-09-09 |
| to        | Yes*     | date | 2025-12-09 |

*Maximum 4000 records per request, Max 90-day date range*

---

## Earnings Transcript

### Latest Earning Transcripts API
Access available earnings transcripts for companies.

**Endpoint:** `https://financialmodelingprep.com/stable/earning-call-transcript-latest`

### Earnings Transcript API
Access the full transcript of a company's earnings call.

**Endpoint:** `https://financialmodelingprep.com/stable/earning-call-transcript?symbol=AAPL&year=2020&quarter=3`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| year      | Yes      | string | 2020    |
| quarter   | Yes      | string | 3       |

### Transcripts Dates By Symbol API
Access earnings call transcript dates for specific companies.

**Endpoint:** `https://financialmodelingprep.com/stable/earning-call-transcript-dates?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Available Transcript Symbols API
Access a complete list of stock symbols with available earnings call transcripts.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings-transcript-list`

---

## News

### FMP Articles API
Access the latest articles from Financial Modeling Prep.

**Endpoint:** `https://financialmodelingprep.com/stable/fmp-articles?page=0&limit=20`

### General News API
Access the latest general news articles from a variety of sources.

**Endpoint:** `https://financialmodelingprep.com/stable/news/general-latest?page=0&limit=20`

### Press Releases API
Access official company press releases.

**Endpoint:** `https://financialmodelingprep.com/stable/news/press-releases-latest?page=0&limit=20`

### Stock News API
Access headlines, snippets, publication URLs, and ticker symbols for stock news.

**Endpoint:** `https://financialmodelingprep.com/stable/news/stock-latest?page=0&limit=20`

### Crypto News API
Access a curated list of cryptocurrency news articles.

**Endpoint:** `https://financialmodelingprep.com/stable/news/crypto-latest?page=0&limit=20`

### Forex News API
Access forex news articles including headlines, snippets, and publication URLs.

**Endpoint:** `https://financialmodelingprep.com/stable/news/forex-latest?page=0&limit=20`

### Search Press Releases API
Search for company press releases by symbol or company name.

**Endpoint:** `https://financialmodelingprep.com/stable/news/press-releases?symbols=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbols   | Yes      | string | AAPL    |

### Search Stock News API
Search for stock-related news by ticker symbol or company name.

**Endpoint:** `https://financialmodelingprep.com/stable/news/stock?symbols=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbols   | Yes      | string | AAPL    |

### Search Crypto News API
Search for cryptocurrency news by coin name or symbol.

**Endpoint:** `https://financialmodelingprep.com/stable/news/crypto?symbols=BTCUSD`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| symbols   | Yes      | string | BTCUSD   |

### Search Forex News API
Search for foreign exchange news by currency pair symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/news/forex?symbols=EURUSD`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| symbols   | Yes      | string | EURUSD   |

---

## Form 13F

### Institutional Ownership Filings API
Track the latest SEC filings related to institutional ownership.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/latest?page=0&limit=100`

### Filings Extract API
Extract detailed data directly from official SEC filings.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/extract?cik=0001388838&year=2023&quarter=3`

| Parameter | Required | Type   | Example      |
|-----------|----------|--------|--------------|
| cik       | Yes      | string | 0001388838   |
| year      | Yes      | string | 2023         |
| quarter   | Yes      | string | 3            |

### Form 13F Filings Dates API
Retrieve dates associated with Form 13F filings by institutional investors.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/dates?cik=0001067983`

| Parameter | Required | Type   | Example      |
|-----------|----------|--------|--------------|
| cik       | Yes      | string | 0001067983   |

### Filings Extract With Analytics By Holder API
Provides an analytical breakdown of institutional filings.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/extract-analytics/holder?symbol=AAPL&year=2023&quarter=3&page=0&limit=10`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| year      | Yes      | string | 2023    |
| quarter   | Yes      | string | 3       |
| page      | No       | number | 0       |
| limit     | No       | number | 10      |

### Holder Performance Summary API
Provides insights into the performance of institutional investors.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/holder-performance-summary?cik=0001067983&page=0`

| Parameter | Required | Type   | Example      |
|-----------|----------|--------|--------------|
| cik       | Yes      | string | 0001067983   |
| page      | No       | number | 0            |

### Holders Industry Breakdown API
Provides an overview of the sectors and industries that institutional holders are investing in.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/holder-industry-breakdown?cik=0001067983&year=2023&quarter=3`

| Parameter | Required | Type   | Example      |
|-----------|----------|--------|--------------|
| cik       | Yes      | string | 0001067983   |
| year      | Yes      | string | 2023         |
| quarter   | Yes      | string | 3            |

### Positions Summary API
Provides a comprehensive snapshot of institutional holdings for a specific stock symbol.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/symbol-positions-summary?symbol=AAPL&year=2023&quarter=3`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| year      | Yes      | string | 2023    |
| quarter   | Yes      | string | 3       |

### Industry Performance Summary API
Provides an overview of how various industries are performing financially.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/industry-summary?year=2023&quarter=3`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | Yes      | string | 2023    |
| quarter   | Yes      | string | 3       |

---

## Analyst

### Financial Estimates API
Retrieve analyst financial estimates for stock symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/analyst-estimates?symbol=AAPL&period=annual&page=0&limit=10`

| Parameter | Required | Type   | Example        |
|-----------|----------|--------|----------------|
| symbol    | Yes      | string | AAPL           |
| period    | Yes      | string | annual/quarter |
| page      | No       | number | 0              |
| limit     | No       | number | 10             |

*Maximum 1000 records per request*

### Ratings Snapshot API
Provides a comprehensive snapshot of financial ratings for stock symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/ratings-snapshot?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

*Maximum 1 record per request*

### Historical Ratings API
Provides access to historical financial ratings for stock symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/ratings-historical?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| limit     | No       | number | 1       |

*Maximum 10000 records per request*

### Price Target Summary API
Provides access to average price targets from analysts across various timeframes.

**Endpoint:** `https://financialmodelingprep.com/stable/price-target-summary?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Price Target Consensus API
Provides high, low, median, and consensus price targets for stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/price-target-consensus?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Stock Grades API
Access the latest stock grades from top analysts and financial institutions.

**Endpoint:** `https://financialmodelingprep.com/stable/grades?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Historical Stock Grades API
Track historical changes in analyst ratings for specific stock symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/grades-historical?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |
| limit     | No       | number | 100     |

*Maximum 1000 records per request*

### Stock Grades Summary API
Provides a consolidated summary of market sentiment for individual stock symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/grades-consensus?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

---

## Market Performance

### Market Sector Performance Snapshot API
Analyze how different industries are performing in the market.

**Endpoint:** `https://financialmodelingprep.com/stable/sector-performance-snapshot?date=2024-02-01`

| Parameter | Required | Type   | Example     |
|-----------|----------|--------|-------------|
| date      | Yes      | string | 2024-02-01  |
| exchange  | No       | string | NASDAQ      |
| sector    | No       | string | Energy      |

### Industry Performance Snapshot API
Analyze trends, movements, and daily performance metrics for specific industries.

**Endpoint:** `https://financialmodelingprep.com/stable/industry-performance-snapshot?date=2024-02-01`

| Parameter | Required | Type   | Example         |
|-----------|----------|--------|-----------------|
| date      | Yes      | string | 2024-02-01      |
| exchange  | No       | string | NASDAQ          |
| industry  | No       | string | Biotechnology   |

### Historical Market Sector Performance API
Review how different sectors have performed over time.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-sector-performance?sector=Energy`

| Parameter | Required | Type   | Example     |
|-----------|----------|--------|-------------|
| from      | No       | string | 2024-02-01  |
| exchange  | No       | string | NASDAQ      |
| sector    | Yes      | string | Energy      |
| to        | No       | string | 2024-03-01  |

### Historical Industry Performance API
Track long-term trends and analyze how different industries have evolved over time.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-industry-performance?industry=Biotechnology`

| Parameter | Required | Type   | Example         |
|-----------|----------|--------|-----------------|
| industry  | Yes      | string | Biotechnology   |
| exchange  | No       | string | NASDAQ          |
| from      | No       | string | 2024-02-01      |
| to        | No       | string | 2024-03-01      |

### Sector PE Snapshot API
Retrieve the price-to-earnings (P/E) ratios for various sectors.

**Endpoint:** `https://financialmodelingprep.com/stable/sector-pe-snapshot?date=2024-02-01`

| Parameter | Required | Type   | Example     |
|-----------|----------|--------|-------------|
| date      | Yes      | string | 2024-02-01  |
| exchange  | No       | string | NASDAQ      |
| sector    | No       | string | Energy      |

### Industry PE Snapshot API
View price-to-earnings (P/E) ratios for different industries.

**Endpoint:** `https://financialmodelingprep.com/stable/industry-pe-snapshot?date=2024-02-01`

| Parameter | Required | Type   | Example         |
|-----------|----------|--------|-----------------|
| date      | Yes      | string | 2024-02-01      |
| exchange  | No       | string | NASDAQ          |
| industry  | No       | string | Biotechnology   |

### Historical Sector PE API
Analyze how sector valuations have evolved over time.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-sector-pe?sector=Energy`

| Parameter | Required | Type   | Example     |
|-----------|----------|--------|-------------|
| from      | No       | string | 2024-02-01  |
| exchange  | No       | string | NASDAQ      |
| sector    | Yes      | string | Energy      |
| to        | No       | string | 2024-03-01  |

### Historical Industry PE API
Track valuation trends across various industries.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-industry-pe?industry=Biotechnology`

| Parameter | Required | Type   | Example         |
|-----------|----------|--------|-----------------|
| industry  | Yes      | string | Biotechnology   |
| exchange  | No       | string | NASDAQ          |
| from      | No       | string | 2024-02-01      |
| to        | No       | string | 2024-03-01      |

### Biggest Stock Gainers API
Track the stocks with the largest price increases.

**Endpoint:** `https://financialmodelingprep.com/stable/biggest-gainers`

### Biggest Stock Losers API
Access data on the stocks with the largest price drops.

**Endpoint:** `https://financialmodelingprep.com/stable/biggest-losers`

### Top Traded Stocks API
Identify the companies experiencing the highest trading volumes.

**Endpoint:** `https://financialmodelingprep.com/stable/most-actives`

---

## Technical Indicators

### Simple Moving Average (SMA) API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/sma?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

### Exponential Moving Average (EMA) API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/ema?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

### Weighted Moving Average (WMA) API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/wma?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

### Double Exponential Moving Average (DEMA) API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/dema?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

### Triple Exponential Moving Average (TEMA) API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/tema?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

### Relative Strength Index (RSI) API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/rsi?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

### Standard Deviation API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/standarddeviation?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

### Williams API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/williams?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

### Average Directional Index (ADX) API

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/adx?symbol=AAPL&periodLength=10&timeframe=1day`

| Parameter    | Required | Type   | Example                              |
|--------------|----------|--------|--------------------------------------|
| symbol       | Yes      | string | AAPL                                 |
| periodLength | Yes      | number | 10                                   |
| timeframe    | Yes      | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from         | No       | date   | 2025-09-09                           |
| to           | No       | date   | 2025-12-09                           |

---

## ETF and Mutual Funds

### ETF & Fund Holdings API
Get a detailed breakdown of the assets held within ETFs and mutual funds.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/holdings?symbol=SPY`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | SPY     |

### ETF & Mutual Fund Information API
Access comprehensive data on ETFs and mutual funds.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/info?symbol=SPY`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | SPY     |

### ETF & Fund Country Allocation API
Gain insight into how ETFs and mutual funds distribute assets across different countries.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/country-weightings?symbol=SPY`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | SPY     |

### ETF Asset Exposure API
Discover which ETFs hold specific stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/asset-exposure?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### ETF Sector Weighting API
Provides a breakdown of the percentage of an ETF's assets invested in each sector.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/sector-weightings?symbol=SPY`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | SPY     |

### Mutual Fund & ETF Disclosure API
Access the latest disclosures from mutual funds and ETFs.

**Endpoint:** `https://financialmodelingprep.com/stable/funds/disclosure-holders-latest?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Mutual Fund Disclosures API
Access comprehensive disclosure data for mutual funds.

**Endpoint:** `https://financialmodelingprep.com/stable/funds/disclosure?symbol=VWO&year=2023&quarter=4`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | VWO     |
| year      | Yes      | string | 2023    |
| quarter   | Yes      | string | 4       |

### Mutual Fund & ETF Disclosure Name Search API
Search for mutual fund and ETF disclosures by name.

**Endpoint:** `https://financialmodelingprep.com/stable/funds/disclosure-holders-search?name=Federated Hermes Government Income Securities, Inc.`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| name      | Yes      | string | Federated Hermes... |

### Fund & ETF Disclosures by Date API
Retrieve detailed disclosures for mutual funds and ETFs based on filing dates.

**Endpoint:** `https://financialmodelingprep.com/stable/funds/disclosure-dates?symbol=VWO`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | VWO     |

---

## SEC Filings

### Latest 8-K SEC Filings API
Get real-time access to significant company events such as mergers, acquisitions, leadership changes.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-8k?from=2024-01-01&to=2024-03-01&page=0&limit=100`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| from      | Yes      | date   | 2024-01-01 |
| to        | Yes      | date   | 2024-03-01 |
| page      | No       | number | 0          |
| limit     | No       | number | 100        |

### Latest SEC Filings API
Access essential regulatory documents, including financial statements, annual reports, 8-K, 10-K, and 10-Q forms.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-financials?from=2024-01-01&to=2024-03-01&page=0&limit=100`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| from      | Yes      | date   | 2024-01-01 |
| to        | Yes      | date   | 2024-03-01 |
| page      | No       | number | 0          |
| limit     | No       | number | 100        |

### SEC Filings By Form Type API
Search for specific SEC filings by form type.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-search/form-type?formType=8-K&from=2024-01-01&to=2024-03-01&page=0&limit=100`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| formType  | Yes      | string | 8-K        |
| from      | Yes      | date   | 2024-01-01 |
| to        | Yes      | date   | 2024-03-01 |
| page      | No       | number | 0          |
| limit     | No       | number | 100        |

### SEC Filings By Symbol API
Search and retrieve SEC filings by company symbol.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-search/symbol?symbol=AAPL&from=2024-01-01&to=2024-03-01&page=0&limit=100`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | AAPL       |
| from      | Yes      | date   | 2024-01-01 |
| to        | Yes      | date   | 2024-03-01 |
| page      | No       | number | 0          |
| limit     | No       | number | 100        |

### SEC Filings By CIK API
Search for SEC filings using CIK number.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-search/cik?cik=0000320193&from=2024-01-01&to=2024-03-01&page=0&limit=100`

| Parameter | Required | Type   | Example      |
|-----------|----------|--------|--------------|
| cik       | Yes      | string | 0000320193   |
| from      | Yes      | date   | 2024-01-01   |
| to        | Yes      | date   | 2024-03-01   |
| page      | No       | number | 0            |
| limit     | No       | number | 100          |

### SEC Filings By Name API
Search for SEC filings by company or entity name.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-company-search/name?company=Berkshire`

| Parameter | Required | Type   | Example   |
|-----------|----------|--------|-----------|
| company   | Yes      | string | Berkshire |

### SEC Filings Company Search By Symbol API
Find company information and regulatory filings using a stock symbol.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-company-search/symbol?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### SEC Filings Company Search By CIK API
Find company information using a CIK (Central Index Key).

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-company-search/cik?cik=0000320193`

| Parameter | Required | Type   | Example      |
|-----------|----------|--------|--------------|
| cik       | Yes      | string | 0000320193   |

### SEC Company Full Profile API
Retrieve detailed company profiles, including business descriptions, executive details, contact information.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-profile?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Industry Classification List API
Retrieve a comprehensive list of industry classifications, including SIC codes.

**Endpoint:** `https://financialmodelingprep.com/stable/standard-industrial-classification-list`

### Industry Classification Search API
Search and retrieve industry classification details for companies.

**Endpoint:** `https://financialmodelingprep.com/stable/industry-classification-search`

### All Industry Classification API
Access comprehensive industry classification data for companies across all sectors.

**Endpoint:** `https://financialmodelingprep.com/stable/all-industry-classification`

---

## Insider Trades

### Latest Insider Trading API
Access the latest insider trading activity.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading/latest?page=0&limit=100`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| page      | No       | number | 0       |
| limit     | No       | number | 100     |

### Search Insider Trades API
Search insider trading activity by company or symbol.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading/search?page=0&limit=100`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| page      | No       | number | 0       |
| limit     | No       | number | 100     |

### Search Insider Trades by Reporting Name API
Search for insider trading activity by reporting name.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading/reporting-name?name=Zuckerberg`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| name      | Yes      | string | Zuckerberg |

### All Insider Transaction Types API
Access a comprehensive list of insider transaction types.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading-transaction-type`

### Insider Trade Statistics API
Analyze insider trading activity with key statistics.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading/statistics?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Acquisition Ownership API
Track changes in stock ownership during acquisitions.

**Endpoint:** `https://financialmodelingprep.com/stable/acquisition-of-beneficial-ownership?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

---

## Indexes

### Stock Market Indexes List API
Retrieve a comprehensive list of stock market indexes across global exchanges.

**Endpoint:** `https://financialmodelingprep.com/stable/index-list`

### Index Quote API
Access real-time stock index quotes.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=^GSPC`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | ^GSPC   |

### Index Short Quote API
Access concise stock index quotes.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=^GSPC`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | ^GSPC   |

### All Index Quotes API
Provides real-time quotes for a wide range of stock indexes.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-index-quotes`

| Parameter | Required | Type    | Example |
|-----------|----------|---------|---------|
| short     | Yes      | boolean | true    |

### Historical Index Light Chart API
Retrieve end-of-day historical prices for stock indexes.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=^GSPC`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | ^GSPC      |
| from      | No       | date   | 2025-09-09 |
| to        | No       | date   | 2025-12-09 |

*Maximum 5000 records per request*

### Historical Index Full Chart API
Access full historical end-of-day prices for stock indexes.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=^GSPC`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | ^GSPC      |
| from      | No       | date   | 2025-09-09 |
| to        | No       | date   | 2025-12-09 |

*Maximum 5000 records per request*

### 1-Minute Interval Index Price API
Retrieve 1-minute interval intraday data for stock indexes.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=^GSPC`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | ^GSPC      |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

### 5-Minute Interval Index Price API
Retrieve 5-minute interval intraday price data for stock indexes.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=^GSPC`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | ^GSPC      |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

### 1-Hour Interval Index Price API
Access 1-hour interval intraday data for stock indexes.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=^GSPC`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | ^GSPC      |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

### S&P 500 Index API
Access detailed data on the S&P 500 index.

**Endpoint:** `https://financialmodelingprep.com/stable/sp500-constituent`

### Nasdaq Index API
Access comprehensive data for the Nasdaq index.

**Endpoint:** `https://financialmodelingprep.com/stable/nasdaq-constituent`

### Dow Jones API
Access data on the Dow Jones Industrial Average.

**Endpoint:** `https://financialmodelingprep.com/stable/dowjones-constituent`

### Historical S&P 500 API
Retrieve historical data for the S&P 500 index.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-sp500-constituent`

### Historical Nasdaq API
Access historical data for the Nasdaq index.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-nasdaq-constituent`

### Historical Dow Jones API
Access historical data for the Dow Jones Industrial Average.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-dowjones-constituent`

---

## Market Hours

### Global Exchange Market Hours API
Retrieve trading hours for specific stock exchanges.

**Endpoint:** `https://financialmodelingprep.com/stable/exchange-market-hours?exchange=NASDAQ`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| exchange  | Yes      | string | NASDAQ   |

### Holidays By Exchange API

**Endpoint:** `https://financialmodelingprep.com/stable/holidays-by-exchange?exchange=NASDAQ`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| exchange  | Yes      | string | NASDAQ   |

### All Exchange Market Hours API
View the market hours for all exchanges.

**Endpoint:** `https://financialmodelingprep.com/stable/all-exchange-market-hours`

---

## Commodity

### Commodities List API
Access an extensive list of tracked commodities.

**Endpoint:** `https://financialmodelingprep.com/stable/commodities-list`

### Commodities Quote API
Access real-time price quotes for all commodities traded worldwide.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=GCUSD`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | GCUSD   |

### Commodities Quote Short API
Get fast and accurate quotes for commodities.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=GCUSD`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | GCUSD   |

### All Commodities Quotes API
Access real-time quotes for multiple commodities at once.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-commodity-quotes`

### Light Chart API
Access historical end-of-day prices for various commodities.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=GCUSD`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | GCUSD   |

### Full Chart API
Access full historical end-of-day price data for commodities.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=GCUSD`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | GCUSD   |

### 1-Minute Interval Commodities Chart API
Track real-time, short-term price movements for commodities.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=GCUSD`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | GCUSD   |

### 5-Minute Interval Commodities Chart API
Monitor short-term price movements with 5-minute interval data.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=GCUSD`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | GCUSD   |

### 1-Hour Interval Commodities Chart API
Monitor hourly price movements and trends.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=GCUSD`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | GCUSD   |

---

## Discounted Cash Flow

### DCF Valuation API
Estimate the intrinsic value of a company.

**Endpoint:** `https://financialmodelingprep.com/stable/discounted-cash-flow?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Levered DCF API
Analyze a company's value incorporating the impact of debt.

**Endpoint:** `https://financialmodelingprep.com/stable/levered-discounted-cash-flow?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Custom DCF Advanced API
Run a tailored Discounted Cash Flow (DCF) analysis with detailed inputs.

**Endpoint:** `https://financialmodelingprep.com/stable/custom-discounted-cash-flow?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Custom DCF Levered API
Run a tailored Levered Discounted Cash Flow (DCF) analysis.

**Endpoint:** `https://financialmodelingprep.com/stable/custom-levered-discounted-cash-flow?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

---

## Forex

### Forex Currency Pairs API
Access a comprehensive list of all currency pairs traded on the forex market.

**Endpoint:** `https://financialmodelingprep.com/stable/forex-list`

### Forex Quote API
Access real-time forex quotes for currency pairs.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=EURUSD`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| symbol    | Yes      | string | EURUSD   |

### Forex Short Quote API
Quickly access concise forex pair quotes.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=EURUSD`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| symbol    | Yes      | string | EURUSD   |

### Batch Forex Quotes API
Access real-time quotes for multiple forex pairs simultaneously.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-forex-quotes`

| Parameter | Required | Type    | Example |
|-----------|----------|---------|---------|
| short     | Yes      | boolean | true    |

### Historical Forex Light Chart API
Access historical end-of-day forex prices.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=EURUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | EURUSD     |
| from      | No       | date   | 2025-09-09 |
| to        | No       | date   | 2025-12-09 |

*Maximum 5000 records per request*

### Historical Forex Full Chart API
Access comprehensive historical end-of-day forex price data.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=EURUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | EURUSD     |
| from      | No       | date   | 2025-09-09 |
| to        | No       | date   | 2025-12-09 |

*Maximum 5000 records per request*

### 1-Minute Interval Forex Chart API
Access real-time 1-minute intraday forex data.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=EURUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | EURUSD     |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

### 5-Minute Interval Forex Chart API
Track short-term forex trends with 5-minute intraday data.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=EURUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | EURUSD     |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

### 1-Hour Interval Forex Chart API
Track forex price movements over the trading day with hourly data.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=EURUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | EURUSD     |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

---

## Crypto

### Cryptocurrency List API
Access a comprehensive list of all cryptocurrencies traded on exchanges worldwide.

**Endpoint:** `https://financialmodelingprep.com/stable/cryptocurrency-list`

### Full Cryptocurrency Quote API
Access real-time quotes for all cryptocurrencies.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=BTCUSD`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| symbol    | Yes      | string | BTCUSD   |

### Cryptocurrency Quote Short API
Access real-time cryptocurrency quotes.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=BTCUSD`

| Parameter | Required | Type   | Example  |
|-----------|----------|--------|----------|
| symbol    | Yes      | string | BTCUSD   |

### All Cryptocurrencies Quotes API
Access live price data for a wide range of cryptocurrencies.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-crypto-quotes`

| Parameter | Required | Type    | Example |
|-----------|----------|---------|---------|
| short     | Yes      | boolean | true    |

### Historical Cryptocurrency Light Chart API
Access historical end-of-day prices for a variety of cryptocurrencies.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=BTCUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | BTCUSD     |
| from      | No       | date   | 2025-09-09 |
| to        | No       | date   | 2025-12-09 |

*Maximum 5000 records per request*

### Historical Cryptocurrency Full Chart API
Access comprehensive end-of-day (EOD) price data for cryptocurrencies.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=BTCUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | BTCUSD     |
| from      | No       | date   | 2025-09-09 |
| to        | No       | date   | 2025-12-09 |

*Maximum 5000 records per request*

### 1-Minute Interval Cryptocurrency Data API
Get real-time, 1-minute interval price data for cryptocurrencies.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=BTCUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | BTCUSD     |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

### 5-Minute Interval Cryptocurrency Data API
Analyze short-term price trends with 5-minute interval data.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=BTCUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | BTCUSD     |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

### 1-Hour Interval Cryptocurrency Data API
Access detailed 1-hour intraday price data for cryptocurrencies.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=BTCUSD`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| symbol    | Yes      | string | BTCUSD     |
| from      | No       | date   | 2024-01-01 |
| to        | No       | date   | 2024-03-01 |

---

## Senate

### Latest Senate Financial Disclosures API
Access the latest financial disclosures from U.S. Senate members.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-latest?page=0&limit=100`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| page      | No       | number | 0       |
| limit     | No       | number | 100     |

### Latest House Financial Disclosures API
Access real-time financial disclosures from U.S. House members.

**Endpoint:** `https://financialmodelingprep.com/stable/house-latest?page=0&limit=100`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| page      | No       | number | 0       |
| limit     | No       | number | 100     |

### Senate Trading Activity API
Monitor the trading activity of US Senators.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-trades?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### Senate Trades By Name API

**Endpoint:** `https://financialmodelingprep.com/stable/senate-trades-by-name?name=Jerry`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| name      | Yes      | string | Jerry   |

### U.S. House Trades API
Track the financial trades made by U.S. House members and their families.

**Endpoint:** `https://financialmodelingprep.com/stable/house-trades?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### House Trades By Name API

**Endpoint:** `https://financialmodelingprep.com/stable/house-trades-by-name?name=James`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| name      | Yes      | string | James   |

---

## ESG

### ESG Investment Search API
Discover companies and funds based on Environmental, Social, and Governance (ESG) scores.

**Endpoint:** `https://financialmodelingprep.com/stable/esg-disclosures?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### ESG Ratings API
Access comprehensive ESG ratings for companies and funds.

**Endpoint:** `https://financialmodelingprep.com/stable/esg-ratings?symbol=AAPL`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| symbol    | Yes      | string | AAPL    |

### ESG Benchmark Comparison API
Evaluate the ESG performance of companies and funds.

**Endpoint:** `https://financialmodelingprep.com/stable/esg-benchmark`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | Yes      | string | 2023    |

---

## Commitment Of Traders

### COT Report API
Access comprehensive Commitment of Traders (COT) reports.

**Endpoint:** `https://financialmodelingprep.com/stable/commitment-of-traders-report`

### COT Analysis By Dates API
Gain in-depth insights into market sentiment with COT report analysis.

**Endpoint:** `https://financialmodelingprep.com/stable/commitment-of-traders-analysis`

### COT Report List API
Access a comprehensive list of available Commitment of Traders (COT) reports.

**Endpoint:** `https://financialmodelingprep.com/stable/commitment-of-traders-list`

---

## Fundraisers

### Latest Crowdfunding Campaigns API
Discover the most recent crowdfunding campaigns.

**Endpoint:** `https://financialmodelingprep.com/stable/crowdfunding-offerings-latest?page=0&limit=100`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| page      | No       | number | 0       |
| limit     | No       | number | 100     |

### Crowdfunding Campaign Search API
Search for crowdfunding campaigns by company name, campaign name, or platform.

**Endpoint:** `https://financialmodelingprep.com/stable/crowdfunding-offerings-search?name=enotap`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| name      | Yes      | string | enotap  |

### Crowdfunding By CIK API
Access detailed information on all crowdfunding campaigns launched by a specific company.

**Endpoint:** `https://financialmodelingprep.com/stable/crowdfunding-offerings?cik=0001916078`

| Parameter | Required | Type   | Example      |
|-----------|----------|--------|--------------|
| cik       | Yes      | string | 0001916078   |

### Equity Offering Updates API
Stay informed about the latest equity offerings.

**Endpoint:** `https://financialmodelingprep.com/stable/fundraising-latest?page=0&limit=10`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| page      | No       | number | 0       |
| limit     | No       | number | 10      |

### Equity Offering Search API
Search for equity offerings by company name or stock symbol.

**Endpoint:** `https://financialmodelingprep.com/stable/fundraising-search?name=NJOY`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| name      | Yes      | string | NJOY    |

### Equity Offering By CIK API
Access detailed information on equity offerings announced by specific companies.

**Endpoint:** `https://financialmodelingprep.com/stable/fundraising?cik=0001547416`

| Parameter | Required | Type   | Example      |
|-----------|----------|--------|--------------|
| cik       | Yes      | string | 0001547416   |

---

## Bulk

### Company Profile Bulk API
Retrieve comprehensive company profile data in bulk.

**Endpoint:** `https://financialmodelingprep.com/stable/profile-bulk?part=0`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| part      | No       | string | 0       |

### Stock Rating Bulk API
Provides comprehensive rating data for multiple stocks in a single request.

**Endpoint:** `https://financialmodelingprep.com/stable/rating-bulk`

### DCF Valuations Bulk API
Retrieve discounted cash flow (DCF) valuations for multiple symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/dcf-bulk`

### Financial Scores Bulk API
Retrieve a wide range of key financial scores and metrics for multiple symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/scores-bulk`

### Price Target Summary Bulk API
Provides a comprehensive overview of price targets for all listed symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/price-target-summary-bulk`

### ETF Holder Bulk API
Retrieve detailed information about the assets and shares held by ETFs.

**Endpoint:** `https://financialmodelingprep.com/stable/etf-holder-bulk?part=1`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| part      | No       | string | 1       |

### Upgrades Downgrades Consensus Bulk API
Provides a comprehensive view of analyst ratings across all symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/upgrades-downgrades-consensus-bulk`

### Key Metrics TTM Bulk API
Retrieve trailing twelve months (TTM) data for all companies.

**Endpoint:** `https://financialmodelingprep.com/stable/key-metrics-ttm-bulk`

### Ratios TTM Bulk API
Retrieve trailing twelve months (TTM) financial ratios for stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/ratios-ttm-bulk`

### Stock Peers Bulk API
Retrieve a comprehensive list of peer companies for all stocks.

**Endpoint:** `https://financialmodelingprep.com/stable/peers-bulk`

### Earnings Surprises Bulk API
Retrieve bulk data on annual earnings surprises.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings-surprises-bulk?year=2025`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | No       | string | 2025    |

### Income Statement Bulk API
Retrieve detailed income statement data in bulk.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-bulk?year=2025&period=Q1`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | No       | string | 2025    |
| period    | No       | string | Q1      |

### Income Statement Growth Bulk API
Access growth data for income statements across multiple companies.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-growth-bulk?year=2025&period=Q1`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | No       | string | 2025    |
| period    | No       | string | Q1      |

### Balance Sheet Statement Bulk API
Access balance sheet data across multiple companies.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-bulk?year=2025&period=Q1`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | No       | string | 2025    |
| period    | No       | string | Q1      |

### Balance Sheet Statement Growth Bulk API
Retrieve growth data across multiple companies' balance sheets.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-growth-bulk?year=2025&period=Q1`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | No       | string | 2025    |
| period    | No       | string | Q1      |

### Cash Flow Statement Bulk API
Access detailed cash flow reports for a wide range of companies.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-bulk?year=2025&period=Q1`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | No       | string | 2025    |
| period    | No       | string | Q1      |

### Cash Flow Statement Growth Bulk API
Retrieve bulk growth data for cash flow statements.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-growth-bulk?year=2025&period=Q1`

| Parameter | Required | Type   | Example |
|-----------|----------|--------|---------|
| year      | No       | string | 2025    |
| period    | No       | string | Q1      |

### Eod Bulk API
Retrieve end-of-day stock price data for multiple symbols in bulk.

**Endpoint:** `https://financialmodelingprep.com/stable/eod-bulk?date=2024-10-22`

| Parameter | Required | Type   | Example    |
|-----------|----------|--------|------------|
| date      | No       | string | 2024-10-22 |

---

## Documentation Source

This documentation was compiled from the official Financial Modeling Prep API documentation available at [https://site.financialmodelingprep.com/developer/docs](https://site.financialmodelingprep.com/developer/docs).

**Last Updated:** March 19, 2026
