---
tags: [audit, cleaner, de-advertisement, newsletters, ingestion, guardrails]
category: concept
---

# De-Advertisement Cleaner Empirical Audit & Guardrails

This document records the empirical audit of the newsletter de-advertisement system (`apps/engine/ingest/cleaner.py`), tracking production failure modes across 1,327 historical records and detailing the guardrail architecture implemented to prevent data corruption.

---

## Context: The De-Advertisement Pass

The newsletter ingestion pipeline runs raw newsletter bodies through a fast LLM pass (`gemini-3.5-flash-lite`) using `instructor` before downstream analysis agents consume the text. The goal is to strip commercial fluff, sponsored blurbs, and referral links while preserving substantive market data, company earnings reports, and financial analysis.

---

## Empirical Production Audit Findings

An empirical audit of the `newsletter_snapshots` production table (1,327 total records) and runtime LLM behavior revealed three core vulnerabilities:

### 1. Pure Promotional Marketing Emails Produced Corrupted Zero-Length Snapshots
- 5 production snapshots in `newsletter_snapshots` had empty or truncated content (`length < 50` characters).
- 4 records (eToro deposit promo, webinar invite, Stock Analysis free trial offer) were 100% marketing campaigns with zero market news.
- The cleaner correctly identified the entire email as advertising and stripped all content down to `""` (empty string).
- However, `ingest_newsletters()` in `apps/engine/ingest/newsletter.py` still persisted these empty snapshots into Supabase.
- These empty snapshots triggered the weekly audit's `empty_newsletter_content` check (`severity: HIGH`), polluted vector embeddings, and introduced noise into agent RAG retrieval.

### 2. Zero Explainability or Audit Trail in Schema
- The original response model `NewsletterCleaningResponse` returned only `cleaned_content: str` and `ads_removed_count: int`.
- It provided no record of *what* was stripped or *why*, preventing automated validation from distinguishing between legitimate ad removal and accidental deletion of financial news.

### 3. Residual Boilerplate Leakage
- 52 historical snapshots retained newsletter footer fluff such as "Unsubscribe", "Manage your e-mail preferences", and physical mailing address legal disclaimers.
- The original prompt instructed removing sponsored sections and referral links, but did not explicitly cover subscription management footers and address blocks.

### 4. Lack of Catastrophic Over-Stripping Guardrail
- If an LLM hallucination or schema extraction error returned an empty or truncated string for a genuine 10,000-character newsletter, the system would silently store the truncated text, permanently losing financial news.

### 5. Observability Standard Defect
- The cleaner's exception handler logged errors with `logger.error(f"...: {e}")` instead of `logger.exception()`, swallowing tracebacks and preventing automated log auditors from diagnosing transient API errors (e.g. rate limits or token limits).

---

## The Architectural Solution

### 1. Enriched Response Schema & Explicit Pure Ad Classification
`NewsletterCleaningResponse` in `apps/engine/core/models.py` was extended to include:
- `ads_summary: list[str]`: A list of short 1-sentence summaries of each removed advertisement or fluff block.
- `is_pure_ad: bool`: An explicit boolean flag set to `true` when an email is purely promotional with zero financial content.

### 2. Upgraded System Prompt
`DE_ADVERTISEMENT_SYSTEM_PROMPT` in `apps/engine/core/llm/prompts.py` was updated to:
- Mandate verbatim preservation of all numbers, earnings metrics (EPS, revenue), prices, dates, and ticker symbols.
- Explicitly instruct stripping footer boilerplate (unsubscribe links, preference centers, mailing addresses).
- Instruct the model to set `is_pure_ad = true` and `cleaned_content = ""` when the entire email is a marketing pitch.

### 3. Catastrophic Over-Stripping Fallback
In `apps/engine/ingest/cleaner.py`:
- If an input is substantial ($\ge 200$ characters) and the LLM returns $< 50$ characters *without* setting `is_pure_ad = true`, the engine logs a warning and automatically falls back to the original content to prevent data loss.

### 4. Empty & Placeholder Content Short-Circuit
In `apps/engine/ingest/cleaner.py`:
- Empty strings, `None`, and no-content sentinels (`config.NO_CONTENT_FOUND` / `"NO_CONTENT_FOUND"`) short-circuit before client instantiation. This avoids unnecessary LLM calls, eliminates API latency/costs on empty emails, and ensures test suites execute without live credentials.

### 5. Pure Ad Ingestion Filter & Semantic Fragility Coordination
In `apps/engine/ingest/newsletter.py`:
- Cleaned text is returned as `CleanedNewsletterText` (a `str` subclass carrying `is_pure_ad`, `ads_removed_count`, and `ads_summary`).
- Snapshots marked with `is_pure_ad = true` or empty content are discarded before insertion into Supabase.
- Senders of filtered pure ads are recorded to avoid false-positive `SEMANTIC FRAGILITY ALERT` warnings when all messages from a sender on a given day were promotional.

### 6. Database Cleanup
The 5 historical zero-length spam rows in Supabase were purged, bringing empty snapshot count to 0 and resolving the `empty_newsletter_content` weekly audit check.

---

## Verification & Status

- Tested with live Gemini Flash Lite API calls verifying verbatim number preservation, multi-block ad removal with summary explanation, and pure marketing email detection.
- Unit and regression test suite added in `apps/engine/tests/test_cleaner.py` and `apps/engine/tests/test_newsletter.py` (28 passing tests).
- 1,223 total engine tests passing with 88% coverage.

---

## Related

- [[concepts/ingestion]] — newsletter scraping and cleaning pipeline
- [[concepts/weekly-audit]] — automated log and SQL checks monitoring empty snapshots
- [[concepts/hallucination-audit]] — empirical verification of numerical accuracy
- [[concepts/observability-standard]] — traceback logging requirements
