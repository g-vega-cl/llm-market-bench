---
tags: [tool, engine, analysis, thematic, options, correlation]
category: entity
---

# Thematic Beneficiaries

Tool for identifying and formatting thematic beneficiaries based on options and correlation data.

## Overview

This tool analyzes thematic beneficiaries by discovering candidate tickers for a given theme and formatting the results as markdown. It is declared in `packages/config/tools.json` and registered in `CANONICAL_TOOLS_REGISTRY` in `apps/engine/core/llm/tools.py`.

## Key Features

- Discovers candidate tickers for a theme
- Formats thematic beneficiaries as markdown
- Handles institutional holdings data
- Integrates with SEC 13F client for ownership data

## Usage

Used by the engine's analysis pipeline to identify and present thematic beneficiaries.

## Related

- [[entities/sec-13f-client]]
- [[entities/tool-registry]]
- [[entities/engine]]
