---
tags: [architecture, philosophy, auditability, data]
category: concept
---

# Information Auditability

Every single piece of information in the LLM Market Bench platform must be completely auditable. If a user or an automated agent looks at a metric, a trade, or a portfolio state and asks, **"How was this calculated?"** or **"Where did this come from?"**, they must be able to trace it back to its source easily.

## Philosophy

Auditability is not just a feature; it is a core architectural tenet of the platform. Because our trading pipeline runs autonomously using LLMs, trust must be earned through absolute transparency:
- **No Mystery Numbers**: Every calculation (such as portfolio value, realized/unrealized PnL, or consensus weights) must have a clear, reproducible formula and log history.
- **Root-Cause Readiness**: When an anomaly occurs (e.g., an LLM making a bad decision or a trade being rejected), the exact system state, model input/output transcripts, and tool calls must be readily accessible.
- **Traceability of Data**: Every price feed, newsletter snapshot, or market barometer update must be stamped with its origin, retrieval timestamp, and raw payload.

## Mechanisms of Auditability

The platform enforces auditability across several key areas:

### 1. Ingestion Audit Trail
All incoming newsletter feeds, economic calendar events, and market snapshots are preserved:
- Raw emails are stored in the database (`newsletter_snapshots` table) with original headers and content.
- Pre-processed text and RAG-embedded chunks link back to their parent snapshot IDs.
- *Audit path*: Web UI Daily Intelligence Briefing -> DB table `newsletter_snapshots` -> Ingestion logs.

### 2. LLM Decision & Tool Execution Logging
Every LLM decision is backed by a full execution history:
- Log messages captured during pipeline execution are stored in `ingestion_logs` in Supabase.
- Tool-calling sequences (including parameters and returned JSON) are checked via hard tool enforcement and logged.
- *Audit path*: Agent decision -> Supabase logs -> Hard tool enforcement logs (showing exactly what tools were called).

### 3. Trade Attribution & PnL History
When a trade is executed, it is linked to the exact decision context:
- Every trade record contains references to the LLM agent that initiated it, the current market prices at execution, and the realized/unrealized calculations.
- Order statuses are synced decoupled via broker status records (`alpaca_order_id`).
- *Audit path*: Portfolio PnL -> Trade ledger -> Alpaca order status -> DB audit trail.

### 4. Observability and Automated Auditing
Our logs are actively audited:
- Weekly automated `audit` loops parse system/model anomalies.
- Hardened stack traces are output via `logger.exception()` to ensure root-cause analysis is straightforward.

## Related

- [[concepts/hallucination-audit]]
- [[concepts/observability-standard]]
- [[concepts/agent-workflow]]
- [[entities/pipeline]]
- [[entities/database]]
