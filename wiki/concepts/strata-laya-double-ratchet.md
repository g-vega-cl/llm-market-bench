---
tags: [autoresearch, double-ratchet, curriculum, tournament, checkpoint, resume]
category: concept
---

# Strata-Laya Double Ratchet

The double-ratchet is the curriculum-tournament loop used by the local autoresearch
system to co-evolve an ingestion prompt and a JEV decision-criteria pair against
historical trading sessions. Each iteration proposes a mutation (via Strata), evaluates
it on a rotating curriculum batch (via Laya), and only "ratchets" the champion forward
when the candidate beats the incumbent score. Because a full tournament can run many
iterations over many weeks of sessions, the loop is checkpointed so it can be resumed
across process restarts.

## Tournament Structure

- **Production Newsletter Scale Prompt 1 (~1,000–1,500 words)** — the ingestion prompt (`DEFAULT_INGESTION_SYSTEM_PROMPT` in `apps/engine/local_autoresearch/document_builder.py`) produces comprehensive cross-asset briefings matching the 5 canonical production newsletter sections (Macro & Yield Trajectory, Multi-Day Trend & Overnight Tape, Options Positioning, Institutional Consensus & Lessons, and Directional Tension). It runs without token reasoning caps (`reasoning_budget_tokens: -1`), preserving Qwen 32B's full analytical depth.
- **Batch 0 baseline** — the initial ingestion prompt + criteria pair is evaluated on
  the first curriculum batch and becomes the starting champion (history entry 0).
- **Iteration loop** — for `it` in `start_it .. iterations-1`, a batch is selected
  round-robin (`it % len(batches)`), a mutation is generated with Strata, evaluated on
  that batch, and accepted only if it improves the champion score.
- **Early Pruning** — unviable candidate mutations that exhibit <= 25% win rate after a minimum number of weeks (`early_prune_min_weeks=2`) or that cannot mathematically exceed the champion win rate are aborted early. Pruned candidates are strictly barred from becoming champion. See [[concepts/early-pruning]].
- **Stashed test weeks** — a held-out slice is evaluated at the end to report
  out-of-sample performance.

## Checkpoint & Resume

The tournament persists state to a JSON checkpoint file (default
`.double_ratchet_curriculum_state.json`, overridable via the `state_path` argument or
the `DOUBLE_RATCHET_CURRICULUM_STATE` environment variable). The checkpoint records
`last_completed_iteration`, `total_iterations`, the champion score, the champion
ingestion prompt, the champion criteria config, the champion metrics, and the full
history.

On startup the loop inspects the checkpoint file:

- If a valid checkpoint exists with `0 < last_completed_iteration < iterations`, the
  run **resumes**: it restores the champion prompt/criteria/metrics and history, sets
  `start_it = last_completed_iteration + 1`, and skips the Batch 0 baseline evaluation
  entirely (the baseline is reconstructed from `history[0]`).
- Otherwise it starts fresh at `start_it = 1`, evaluates the Batch 0 baseline, seeds
  history, and writes the initial checkpoint.

A single-pass dry run (`iterations <= 1`) still returns immediately after the baseline
without entering the iteration loop.

Resume is validated by `test_run_double_ratchet_curriculum_tournament_resume`, which
seeds a checkpoint at iteration 2 and asserts that only the remaining iteration plus
the stashed test evaluation are executed, and that the champion score/prompt are
restored from the checkpoint.

## Related

- [[entities/local-autoresearch]]
- [[entities/autoresearch]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/jev-decisions-model]]
- [[concepts/laya-decisions-model]]
