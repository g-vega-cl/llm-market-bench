---
tags: [autoresearch, evaluation, out-of-distribution, regime, stress-testing]
category: concept
---

# Regime Vault

The Regime Vault is a held-out, out-of-distribution evaluation set used by [[entities/local-autoresearch]] to stress-test a champion prompt/manifest across prior market regimes, rather than only the recent homogeneous dataset slice.

## Dual-Track Arena

| Track | Window | Characteristics |
| :--- | :--- | :--- |
| Primary Arena | Oct 2024 – Oct 2026 (~500 days) | High-resolution 09:15 ET pre-market tape, prior-session technicals, morning news |
| Regime Vault | 2021 – 2024 (~800+ days) | Pure macro/narrative setups, pre-market tape omitted entirely |

The vault is compiled with `build_cache_from_raw_db(..., is_regime_vault=True)`, which drops the pre-market quote block completely — including the 09:30 open — so the model must reason from macro series, prior-session profile, and narrative only. This prevents any lookahead that would not have been available in that era.

## Purpose

Candidates that beat the primary-arena baseline are re-evaluated on the vault. A mutation that improves the primary score but fails the vault is rejected as an overfit, keeping the incumbent baseline. This gives a cheap guard against tactics that only work in the recent regime.

## CLI

```sh
# Compile the held-out vault cache (no pre-market tape leakage)
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --build-historical-cache --regime-vault --vault-cache-db .regime_vault_cache.db \
  --start-date 2021-02-15 --end-date 2024-09-30

# Score the current active baseline against the vault
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --eval-vault --vault-cache-db .regime_vault_cache.db
```

evaluate_baseline_on_vault prints a report with the vault score, traded win rate, gated `NO_TRADE` days, and the baseline hypothesis.

## Related

- [[entities/local-autoresearch]] — the arena that uses this vault
- [[concepts/locked-vault-kfold]] — K-fold evaluation on cached weeks
- [[concepts/zero-lookahead-materialization]] — the point-in-time contract the vault relies on
- [[entities/historical-downloader]] — supplies the raw rows the vault is built from
