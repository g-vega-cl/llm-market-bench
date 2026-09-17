---
tags: [entity, engine, sec, 13f, institutional-holdings, edgar]
category: entity
---

# SEC 13F Client

Client for fetching and parsing SEC Form 13F filings from EDGAR, including institutional holdings and thematic beneficiary data.

## Overview

This module provides a client for interacting with SEC EDGAR to retrieve and parse Form 13F filings. It handles XML parsing of 13F information tables and supports matching co-ownership of securities across funds.

## Key Features

- Fetches 13F filings from SEC EDGAR
- Parses 13F information table XML
- Matches co-ownership of securities across funds
- Integrates with thematic beneficiary analysis

## Usage

Used by the engine's analysis pipeline to retrieve institutional holdings data for thematic beneficiary identification.

## Related

- [[entities/thematic-beneficiaries]]
- [[entities/engine]]
