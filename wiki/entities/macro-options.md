---
tags: [macro, options, market-data, engine]
category: entity
---

# Macro Options

Macro Options is a module in the engine that fetches and formats macro options data, including economic indicators and market context, for use in analysis and reporting.

## Overview

This component retrieves macro options metrics from external data sources, caches responses, and formats them into markdown tables for terminal or markdown summaries. It supports multiple tickers and handles empty result sets gracefully.

## Key Features

- Fetches macro options metrics via external APIs
- Caches responses to avoid redundant network calls
- Formats metrics into dense markdown tables
- Handles empty and unexpected response formats

## Usage

Used by the engine's analysis pipeline to enrich market context with macro-level options data. The formatted tables are included in reports and newsletters.

## Related

- [[entities/economic-releases]]
- [[entities/engine]]
