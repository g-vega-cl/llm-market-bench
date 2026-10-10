---
tags: [concept, daily-predictor, autoresearch, feature-selection, jev]
category: concept
---

# Curated Data Manifest ("Box of Data")

A **Data Manifest** is a declarative description of exactly which information modules are packed into the pre-market context sent to a prediction model. It converts "what data does the model see?" from an implicit property of the pipeline into an explicit, evolvable configuration object.

## Schema

`DataManifest` (`apps/engine/local_autoresearch/manifest.py`) is a Pydantic model with per-source toggles:

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `selected_newsletters` | `None` (all) | Allow-list of newsletter senders to include |
| `include_synthetic_newsletter` | `true` | AI Wall Street morning briefing |
| `include_macro_proxies` | `QQQ, DIA, IWM, TLT, IEF, GLD, USO` | Benchmark proxies to include |
| `include_currency_uup` | `false` | US Dollar index (UUP) pre-market gap |
| `include_options_derivatives` | `true` | Max Pain, Put/Call, 25-delta skew |
| `include_economic_calendar` | `true` | High-impact economic releases |
| `include_market_health_barometer` | `false` | Index breadth / valuation barometer |
| `include_recent_market_feeling` | `false` | Qualitative market feeling text |
| `include_intraday_profile` | `true` | Prior-session VWAP, CLV, candle archetype |

The available newsletter senders are enumerated in `KNOWN_NEWSLETTER_SENDERS`.

## Compilation

`pack_daily_context(day_record, manifest)` deterministically compiles the manifest against a point-in-time daily record into a formatted context string. It enforces the **zero-lookahead guarantee**: only fields captured before 09:15 AM ET on the target date are eligible. The same `day_record` plus `manifest` always produces identical text.

The live version of this record is assembled by `get_structured_daily_market_context()` in `apps/engine/tasks/daily_predictor.py`, which returns both the full narrative context and a structured `data_record` (economic calendar, synthetic newsletter, newsletters, proxies, options sentiment, intraday profile, barometer, market feeling). Standard models receive the full narrative; `jev-local-autoresearched` receives only the manifest-filtered subset.

## Role in Autoresearch

The manifest is one of two levers the meta-researcher mutates (the other being [[concepts/confidence-gating]]) via the `AutoresearchMutation` schema. Pruning noisy inputs — dropping FX (`UUP`), lower-signal newsletter senders, or the barometer — is often as valuable as adding signals. The seeded local champion pruned 13 of 15 newsletter senders down to `Sherwood News` and `Chartr`, kept `QQQ`/`IWM`, and excluded `UUP`, the barometer, and market feeling.

## Presentation

The active manifest is stored inside `prompt_experiments.prompt_content` and parsed on the web via `parseCuratedManifest()`. `CuratedManifestCard.tsx` renders the included newsletters, proxies, and active feature signals as badges, so the arena visibly shows which "Box of Data" the champion is reasoning over.

## Related

- [[entities/local-autoresearch]] — the loop that mutates the manifest
- [[concepts/locked-vault-kfold]] — the scoring that selects winning manifests
- [[concepts/jev-decisions-model]] — the model consuming the manifest
- [[concepts/unified-daily-predictor]] — the arena hosting the curated champion
- [[entities/daily-market-predictor]] — the predictor that compiles the record
