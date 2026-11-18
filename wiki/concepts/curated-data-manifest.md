---
tags: [concept, daily-predictor, autoresearch, feature-selection, jev]
category: concept
---

# Curated Data Manifest ("Box of Data")

> [!NOTE]
> The four-regime champion track that consumed this manifest was retired on 2026-11-18. The manifest schema and packing code remain as research tooling for the offline Strata ratchet; nothing in the daily arena produces curated-manifest predictions today.

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

The live version of this record is assembled by `get_structured_daily_market_context()` in `apps/engine/tasks/daily_predictor.py`, which returns both the full narrative context and a structured `data_record` (economic calendar, synthetic newsletter, newsletters, proxies, options sentiment, intraday profile, barometer, market feeling).

## Role in Autoresearch

The manifest is one of two levers the meta-researcher mutates (the other being [[concepts/confidence-gating]]) via the `AutoresearchMutation` schema. Pruning noisy inputs — dropping FX (`UUP`), lower-signal newsletter senders, or the barometer — is often as valuable as adding signals. The retired `jev-four-regime-champion` manifest pruned the newsletter set down to `Sherwood News` and `Chartr`, kept `QQQ`/`IWM`, and excluded `UUP`, the barometer, and market feeling.

## Presentation

The manifest is stored inside `prompt_experiments.prompt_content` for the offline Strata ratchet. The former web-side `parseCuratedManifest()` helper and `CuratedManifestCard.tsx` component were removed on 2026-11-18 along with the four-regime champion tab, so no live arena surface renders a curated manifest today.

## Related

- [[entities/local-autoresearch]] — the loop that mutates the manifest
- [[concepts/locked-vault-kfold]] — the scoring that selects winning manifests
- [[concepts/jev-decisions-model]] — the model that consumed the manifest
- [[concepts/unified-daily-predictor]] — the arena hosting the model tabs
- [[entities/daily-market-predictor]] — the predictor that compiles the record
