---
tags: [concept, auto-research, memory, context]
category: concept
---

# State Ledger Injection

To solve the "context black hole" problem in our agentic pipelines (particularly for the auto-research agent), the system employs **State Ledger Injection**.

## The Problem

Agents operate statelessly. When an agent inherits a portfolio from a prior session (or a previous weekly prompt), it knows *what* it holds (the positions) but lacks the context of *why* it holds them. Without knowing the original thesis, the entry plan, or the expected holding period, an agent might prematurely liquidate a long-term position simply because it wasn't the one that entered the trade.

## The Solution

State Ledger Injection reconstructs the historical narrative for every active holding and injects it directly into the agent's system prompt before inference.

1. **Attribution Aggregation**: Using `get_active_ledger_xml` in the `attribution/service.py` module, the system queries the `portfolio_positions` table for all currently held tickers. It dynamically inspects and awaits table queries to support both synchronous `Client` and asynchronous `AsyncClient` Supabase connection objects.
2. **Historical Construction**: It then fetches the historical chronological sequence of `decisions` that led to the current position (including `BUY`, `SELL`, `HOLD` actions, their associated `reasoning`, and `advance_planning` notes).
3. **XML Formatting**: This data is aggregated into a structured `<CURRENT_PORTFOLIO_LEDGER>` XML block.
4. **Prompt Injection**: The `prompt_factory.py` automatically fetches this XML block and appends it to the active system prompt.

## Agent Behavior

The `CORE_ANALYSIS_SYSTEM_PROMPT` explicitly instructs agents to review the `<CURRENT_PORTFOLIO_LEDGER>`. The agent must evaluate whether the original thesis for an inherited position is "intact" or "broken" based on new market data, before deciding to hold, add, or liquidate.

## Related

- [[entities/autoresearch]] — Beneficiary of the state ledger
- [[concepts/rag-strategy]] — Tiered context injection mechanism
