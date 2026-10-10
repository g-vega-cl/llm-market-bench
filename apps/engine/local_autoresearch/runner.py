"""Top-level Orchestrator CLI for Local Autoresearch (Qwen via Strata + Jev on OpenRouter)."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.engine.local_autoresearch.cache_builder import (
    DEFAULT_CACHE_DB,
    build_cache_from_supabase,
    load_cached_weeks,
)
from apps.engine.local_autoresearch.jev_evaluator import (
    evaluate_vault,
    evaluate_weekly_kfold,
    split_weekly_vault,
)
from apps.engine.local_autoresearch.local_store import (
    DEFAULT_LOCAL_DB,
    format_memories_for_prompt,
    get_active_baseline,
    get_recent_memories,
    save_local_experiment,
    save_local_memory,
)
from apps.engine.local_autoresearch.manifest import (
    DataManifest,
    JevCriteriaConfig,
)
from apps.engine.local_autoresearch.reporting import (
    render_terminal_dashboard,
    update_dashboard_artifact,
)
from apps.engine.local_autoresearch.strata_client import (
    DEFAULT_STRATA_URL,
    generate_mutation_with_strata,
    is_strata_available,
)

from core.config import logger
from core.db import get_supabase_client
from core.llm.daily_predictor_prompts import format_jev_curated_prompt_content

DEFAULT_ARTIFACT_PATH = (
    "/home/cv/.gemini/antigravity-cli/brain/91f7fa65-7a3b-4e8d-b3b0-2f054a18670d/local_autoresearch_dashboard.md"
)

CLEAN_SHEET_INITIAL_CRITERIA = JevCriteriaConfig(
    criteria_up="Close price >= Open price. Predict UP if SPY will close HIGHER at 4:00 PM ET compared to 9:30 AM ET Open.",
    criteria_down="Close price < Open price. Predict DOWN if SPY will close LOWER at 4:00 PM ET compared to 9:30 AM ET Open.",
    min_confidence=50.0,
)


async def run_local_autoresearch_loop(
    iterations: int = 5,
    cache_db: str = DEFAULT_CACHE_DB,
    local_db: str = DEFAULT_LOCAL_DB,
    strata_url: str = DEFAULT_STRATA_URL,
    promote_best: bool = False,
    seed: int = 42,
    max_concurrency: int = 10,
    artifact_path: str = DEFAULT_ARTIFACT_PATH,
) -> dict[str, Any]:
    """Execute the autonomous local prompt & manifest improvement loop."""
    logger.info(f"=== Starting Local Autoresearch: {iterations} iterations ===")

    # 1. Load cached weekly blocks and partition Locked Vault
    weeks_data = load_cached_weeks(cache_db)
    if not weeks_data:
        raise RuntimeError(
            f"No cached trading days found in {cache_db}. Run with --init-cache first to populate from Supabase."
        )

    active_weeks_data, vault_weeks_data = split_weekly_vault(weeks_data, vault_ratio=0.20, seed=seed)
    total_days = sum(len(days) for days in weeks_data.values())
    active_days = sum(len(days) for days in active_weeks_data.values())
    vault_days = sum(len(days) for days in vault_weeks_data.values())
    logger.info(
        f"Loaded {len(weeks_data)} weekly blocks ({total_days} total trading days). "
        f"Partitioned into {len(active_weeks_data)} Active Optimization Weeks ({active_days} days) "
        f"and {len(vault_weeks_data)} Locked Vault Weeks ({vault_days} days)."
    )

    history: list[dict[str, Any]] = []

    # 2. Check or initialize baseline in local_store
    baseline = get_active_baseline(local_db)
    baseline_vault_score = 0.0
    if not baseline:
        logger.info("Starting from 0 (clean sheet): evaluating bare format blocks to establish baseline...")
        base_manifest = DataManifest()
        seed_eval = await evaluate_weekly_kfold(
            weekly_data=active_weeks_data,
            criteria=CLEAN_SHEET_INITIAL_CRITERIA,
            manifest=base_manifest,
            seed=seed,
            max_concurrency=max_concurrency,
        )
        if vault_weeks_data:
            seed_vault = await evaluate_vault(
                vault_data=vault_weeks_data,
                criteria=CLEAN_SHEET_INITIAL_CRITERIA,
                manifest=base_manifest,
                max_concurrency=max_concurrency,
            )
            baseline_vault_score = seed_vault["score"]
            logger.info(f"Initial Locked Vault Score: {baseline_vault_score:.2f}")

        base_tag = f"clean-start-{uuid.uuid4().hex[:6]}"
        save_local_experiment(
            variant_tag=base_tag,
            criteria=CLEAN_SHEET_INITIAL_CRITERIA,
            manifest=base_manifest,
            train_score=seed_eval["train_metrics"]["score"],
            test_score=seed_eval["test_metrics"]["score"],
            overfit_penalty=seed_eval["overfit_penalty"],
            effective_score=seed_eval["effective_score"],
            is_baseline_beat=True,
            status="baseline",
            hypothesis="Clean sheet start from 0 (bare format blocks, no trading heuristics).",
            db_path=local_db,
        )
        baseline = get_active_baseline(local_db)
        history.append(
            {
                "iteration": 0,
                "variant_tag": base_tag,
                "train_score": seed_eval["train_metrics"]["score"],
                "test_score": seed_eval["test_metrics"]["score"],
                "overfit_penalty": seed_eval["overfit_penalty"],
                "effective_score": seed_eval["effective_score"],
                "vault_score": baseline_vault_score if vault_weeks_data else None,
                "is_baseline_beat": True,
                "hypothesis": "Clean sheet start from 0",
            }
        )
    elif vault_weeks_data:
        curr_crit = JevCriteriaConfig(
            criteria_up=baseline["criteria_up"],
            criteria_down=baseline["criteria_down"],
            min_confidence=baseline["min_confidence"],
        )
        curr_man = DataManifest(**baseline["manifest"])
        seed_vault = await evaluate_vault(
            vault_data=vault_weeks_data,
            criteria=curr_crit,
            manifest=curr_man,
            max_concurrency=max_concurrency,
        )
        baseline_vault_score = seed_vault["score"]

    assert baseline is not None
    current_criteria = JevCriteriaConfig(
        criteria_up=baseline["criteria_up"],
        criteria_down=baseline["criteria_down"],
        min_confidence=baseline["min_confidence"],
    )
    current_manifest = DataManifest(**baseline["manifest"])
    baseline_score = float(baseline.get("effective_score", 0.0))
    current_tag = baseline["variant_tag"]

    if not history:
        history.append(
            {
                "iteration": 0,
                "variant_tag": current_tag,
                "train_score": baseline.get("train_score", 0.0),
                "test_score": baseline.get("test_score", 0.0),
                "overfit_penalty": baseline.get("overfit_penalty", 0.0),
                "effective_score": baseline_score,
                "is_baseline_beat": True,
                "hypothesis": baseline.get("hypothesis", "Active baseline"),
            }
        )

    logger.info(f"Active baseline [{current_tag}]: Canonical Ratchet Score = {baseline_score:.2f}")

    # 3. Execution Loop
    for it in range(1, iterations + 1):
        logger.info(f"\n--- Iteration {it}/{iterations} ---")

        # Gather past local memories
        recent_mems = get_recent_memories(limit=5, db_path=local_db)
        memories_text = format_memories_for_prompt(recent_mems)

        # Query local Qwen via Strata for next mutation
        logger.info("Consulting Local Qwen (Strata) for criteria & manifest mutation...")
        try:
            mutation = await generate_mutation_with_strata(
                baseline_criteria=current_criteria,
                baseline_manifest=current_manifest,
                baseline_score=baseline_score,
                train_score=baseline.get("train_score", 0.0),
                test_score=baseline.get("test_score", 0.0),
                memories_context=memories_text,
                base_url=strata_url,
            )
        except Exception as e:
            logger.error(f"Strata mutation failed on iteration {it}: {e}")
            continue

        cand_tag = f"qwen-jev-{uuid.uuid4().hex[:6]}"
        logger.info(f"Proposed mutation [{cand_tag}]: {mutation.hypothesis}")

        # Evaluate candidate across active weekly blocks using non-chronological K-Fold
        logger.info(f"Simulating Jev decisions across {len(active_weeks_data)} active weeks in parallel...")
        eval_res = await evaluate_weekly_kfold(
            weekly_data=active_weeks_data,
            criteria=mutation.criteria,
            manifest=mutation.manifest,
            seed=seed + it,
            max_concurrency=max_concurrency,
        )

        train_score = eval_res["train_metrics"]["score"]
        test_score = eval_res["test_metrics"]["score"]
        overfit_penalty = eval_res["overfit_penalty"]
        eff_score = eval_res["effective_score"]

        is_winner = eff_score > baseline_score
        cand_vault_score = None
        vault_overfit = False

        if is_winner and vault_weeks_data:
            logger.info("Evaluating candidate on unseen Locked Vault to check generalization...")
            vault_res = await evaluate_vault(
                vault_data=vault_weeks_data,
                criteria=mutation.criteria,
                manifest=mutation.manifest,
                max_concurrency=max_concurrency,
            )
            cand_vault_score = vault_res["score"]
            logger.info(
                f"Locked Vault Evaluation [{cand_tag}]: Vault Score={cand_vault_score:.2f} "
                f"(Baseline Vault={baseline_vault_score:.2f}, Traded WR={vault_res['traded_win_rate_pct']}%)"
            )
            # Gate check: Vault score must maintain solid generalization
            if cand_vault_score < max(40.0, baseline_vault_score - 10.0):
                logger.warning(
                    f"⚠️ OVERFITTING DETECTED! Candidate beat active pool ({eff_score:.2f} > {baseline_score:.2f}) "
                    f"but collapsed on unseen Locked Vault ({cand_vault_score:.2f} < threshold). Discarding!"
                )
                is_winner = False
                vault_overfit = True
            else:
                logger.info(f"🛡️ Vault check PASSED! Generalizes out-of-sample (Vault Score: {cand_vault_score:.2f}).")
                baseline_vault_score = cand_vault_score

        logger.info(
            f"Scorecard [{cand_tag}]: Train={train_score:.2f} | Test={test_score:.2f} | "
            f"Overfit Penalty={overfit_penalty:.2f} => Effective Score={eff_score:.2f} "
            f"(Baseline={baseline_score:.2f})"
        )

        status_desc = "baseline" if is_winner else ("vault_overfit" if vault_overfit else "discarded")
        if is_winner:
            logger.info(f"🏆 RATCHET BEATEN! New baseline established: {eff_score:.2f} > {baseline_score:.2f}")
            vault_desc = f"Vault: {cand_vault_score:.2f}" if cand_vault_score is not None else "No vault"
            insight = (
                f"Beat baseline ({eff_score:.2f} vs {baseline_score:.2f}, {vault_desc}). "
                f"Traded win rate: {eval_res['test_metrics']['traded_win_rate_pct']}%. "
                f"Selected newsletters: {mutation.manifest.selected_newsletters}"
            )
            baseline_score = eff_score
            current_tag = cand_tag
            current_criteria = mutation.criteria
            current_manifest = mutation.manifest
        else:
            logger.info(f"Discarding mutation (status: {status_desc})")
            insight = (
                f"Collapsed on Locked Vault ({cand_vault_score:.2f}) despite beating active pool."
                if vault_overfit
                else f"Failed to beat active baseline ({eff_score:.2f} <= {baseline_score:.2f}). Overfit penalty: {overfit_penalty:.2f}."
            )

        save_local_experiment(
            variant_tag=cand_tag,
            criteria=mutation.criteria,
            manifest=mutation.manifest,
            parent_tag=current_tag,
            train_score=train_score,
            test_score=test_score,
            overfit_penalty=overfit_penalty,
            effective_score=eff_score,
            is_baseline_beat=is_winner,
            status=status_desc,
            hypothesis=mutation.hypothesis,
            db_path=local_db,
        )
        save_local_memory(
            iteration=it,
            variant_tag=cand_tag,
            hypothesis=mutation.hypothesis,
            insight=insight,
            test_score=test_score,
            is_baseline_beat=is_winner,
            db_path=local_db,
        )

        history.append(
            {
                "iteration": it,
                "variant_tag": cand_tag,
                "train_score": train_score,
                "test_score": test_score,
                "overfit_penalty": overfit_penalty,
                "effective_score": eff_score,
                "vault_score": cand_vault_score,
                "is_baseline_beat": is_winner,
                "status_reason": "vault_overfit" if vault_overfit else ("winner" if is_winner else "discarded"),
                "hypothesis": mutation.hypothesis,
            }
        )

        active_bl = get_active_baseline(local_db) or {}
        weekly_b = eval_res.get("weekly_breakdown")
        dashboard_str = render_terminal_dashboard(history, active_bl, latest_weekly_breakdown=weekly_b)
        print(dashboard_str)
        update_dashboard_artifact(history, active_bl, artifact_path, latest_weekly_breakdown=weekly_b)

    best = get_active_baseline(local_db)
    logger.info(
        f"\n=== Autoresearch Completed. Current Best Baseline: {best['variant_tag']} (Score: {best['effective_score']:.2f}) ==="
    )

    # 4. Optional promotion to Supabase
    if promote_best and best:
        try:
            promote_baseline_to_supabase(local_db=local_db)
        except Exception as e:
            logger.error(f"Failed to promote winning baseline to Supabase: {e}")

    return best or {}


def promote_baseline_to_supabase(
    local_db: str = DEFAULT_LOCAL_DB,
    track_id: str = "jev-local-autoresearched",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Promote the winning local baseline to Supabase strictly under track_id without mutating other tracks."""
    best = get_active_baseline(local_db)
    if not best:
        raise ValueError(f"No active baseline found in {local_db} to promote.")

    criteria = {
        "UP": best["criteria_up"],
        "DOWN": best["criteria_down"],
    }
    min_confidence = float(best.get("min_confidence", 50.0))
    manifest = best.get("manifest", {})
    prompt_content = format_jev_curated_prompt_content(
        criteria=criteria,
        min_confidence=min_confidence,
        manifest=manifest,
    )

    tag = f"daily-pred-qwen-local-{uuid.uuid4().hex[:6]}"
    today = datetime.now(UTC).date()
    record = {
        "variant_tag": tag,
        "prompt_name": "DAILY_PREDICTOR_PROMPT",
        "prompt_content": prompt_content,
        "track_id": track_id,
        "week_start": today.isoformat(),
        "week_end": (today + timedelta(days=7)).isoformat(),
        "status": "active",
        "experiment_type": "baseline",
        "change_description": (
            f"Promoted from local Qwen/Strata autoresearch [{best['variant_tag']}]: "
            f"score={best['effective_score']:.2f}. {best.get('hypothesis', '')}"
        ),
    }

    if dry_run:
        logger.info(f"[DRY RUN] Would promote {best['variant_tag']} to track {track_id}: tag={tag}")
        return record

    client = get_supabase_client()
    # Demote only existing active records for this specific track
    client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "DAILY_PREDICTOR_PROMPT").eq(
        "track_id", track_id
    ).eq("status", "active").execute()

    # Insert new record as active baseline
    client.table("prompt_experiments").insert(record).execute()
    logger.info(f"Successfully promoted winning local baseline to Supabase for track {track_id} as {tag}!")
    return record


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Local Autoresearch with Strata and Jev")
    parser.add_argument("--iterations", type=int, default=5, help="Number of research iterations")
    parser.add_argument("--init-cache", action="store_true", help="Materialize cache from Supabase before running")
    parser.add_argument("--limit-cache-days", type=int, default=300, help="Days to pull when initializing cache")
    parser.add_argument("--strata-url", type=str, default=DEFAULT_STRATA_URL, help="Strata local base URL")
    parser.add_argument("--check-strata", action="store_true", help="Probe Strata local server health")
    parser.add_argument("--promote-best", action="store_true", help="Promote highest-scoring variant to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Dry run for promotion without mutating Supabase")
    parser.add_argument("--reset", action="store_true", help="Reset local database to start fresh from clean sheet")
    parser.add_argument("--cache-db", type=str, default=DEFAULT_CACHE_DB, help="Cache SQLite path")
    parser.add_argument("--local-db", type=str, default=DEFAULT_LOCAL_DB, help="Local DB path")
    parser.add_argument("--artifact-path", type=str, default=DEFAULT_ARTIFACT_PATH, help="Path for session artifact")

    args = parser.parse_args()

    if args.reset and os.path.exists(args.local_db):
        os.remove(args.local_db)
        print(f"Reset {args.local_db} (clean sheet start from 0).")

    if args.check_strata:
        is_up = asyncio.run(is_strata_available(args.strata_url))
        print(f"Strata at {args.strata_url} is {'UP and RESPONDING' if is_up else 'OFFLINE or NOT REACHABLE'}")
        return

    if args.init_cache:
        client = get_supabase_client()
        count = asyncio.run(build_cache_from_supabase(client, limit_days=args.limit_cache_days, db_path=args.cache_db))
        print(f"Cache initialization complete: {count} historical days cached in {args.cache_db}.")
        if not any(arg.startswith("--iterations") for arg in sys.argv):
            return

    if args.promote_best and not any(arg.startswith("--iterations") for arg in sys.argv):
        rec = promote_baseline_to_supabase(
            local_db=args.local_db,
            track_id="jev-local-autoresearched",
            dry_run=args.dry_run,
        )
        print(
            f"Promotion {'dry run' if args.dry_run else 'complete'}: {rec['variant_tag']} for track {rec['track_id']}"
        )
        return

    asyncio.run(
        run_local_autoresearch_loop(args.iterations, args.cache_db, args.local_db, args.strata_url, args.promote_best)
    )


if __name__ == "__main__":
    main()
