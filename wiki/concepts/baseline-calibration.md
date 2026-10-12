---
tags: [autoresearch, evaluation, calibration, benchmark]
category: concept
---

# Baseline Calibration

A baseline's stored score is only meaningful for the dataset slice it was measured on. When [[entities/local-autoresearch]] moves from a small development dataset to a much larger multi-regime arena, comparing fresh candidates against a stale watermark produces misleading wins. `--calibrate-baseline` fixes this by re-evaluating the active baseline on the *current* active weeks before the tournament starts.

## Why It Matters

Champions tuned on a homogeneous ~115-day slice can record inflated scores (e.g. `qwen-jev-243de1` at 80.43) that collapse to a normalized ~50.19 when re-scored across a 2-year, ~507-day arena. Without calibration, candidates would only need to clear the old inflated bar, and legitimate improvements would be rejected.

## Behavior

With `--calibrate-baseline`, the runner:

1. Reloads the active baseline's criteria and manifest from the local store.
2. Re-runs `evaluate_weekly_kfold` (and the vault, if loaded) on current weeks.
3. Overwrites the baseline record with the calibrated scores and re-reads it as the benchmark watermark.

The tournament then proceeds normally, requiring candidates to beat the calibrated (not stale) score.

## Related

- [[entities/local-autoresearch]] — implements calibration
- [[concepts/regime-vault]] — the held-out check applied alongside calibration
- [[concepts/multi-seed-archetypes]] — alternative starting points for search
- [[concepts/locked-vault-kfold]] — the K-fold evaluator used during calibration
