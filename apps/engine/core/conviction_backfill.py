"""Recompute conviction scores and realign ratchet baselines from stored history.

Both the one-shot backfill CLI (`apps/engine/scripts/backfill_conviction_scores.py`)
and the sector realignment task (`apps/engine/tasks/realign_predictor_baseline.py`)
need the same three things:

1. Score every evaluated prediction row with [[conviction scoring|core/conviction_scoring.py]].
2. Attribute those rows to the prompt variant that produced them, without letting one
   model's predictions score another model's prompt.
3. Pick a baseline per model track behind the sample-size guard, never a single lucky
   call.

Keeping that logic here means the CLI and the task cannot drift apart.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from core.conviction_scoring import conviction_points, select_baseline_candidate

TRACK_DEFAULT = "track_default"


def is_backtest_tag(tag: str | None) -> bool:
    """Backtest rows never participate in the live ratchet."""
    return bool(tag) and "backtest" in tag.lower()


def as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def recompute_daily_conviction(rows: list[dict]) -> list[tuple[str, float | None]]:
    """Return (id, conviction_score) for each directional or hold row that can be scored."""
    updates: list[tuple[str, float | None]] = []
    for row in rows:
        is_hold = str(row.get("predicted_direction", "")).upper() == "HOLD"
        confidence = row.get("confidence")
        correct = row.get("is_correct")
        if is_hold:
            updates.append((row["id"], 0.0))
        elif confidence is not None and correct is not None:
            updates.append((row["id"], round(conviction_points(confidence, bool(correct)), 4)))
    return updates


def recompute_sector_conviction(rows: list[dict]) -> list[tuple[str, float | None]]:
    """Score the best leg, and the worst leg only when it stated its own probability."""
    updates: list[tuple[str, float | None]] = []
    for row in rows:
        confidence = row.get("confidence")
        percentile = row.get("sector_percentile_score")
        if confidence is None or percentile is None:
            continue

        points = [conviction_points(confidence, float(percentile) >= 50.0)]
        worst_confidence = row.get("worst_confidence")
        worst_percentile = row.get("worst_sector_percentile_score")
        if worst_confidence is not None and worst_percentile is not None:
            points.append(conviction_points(worst_confidence, float(worst_percentile) >= 50.0))

        updates.append((row["id"], round(sum(points) / len(points), 4)))
    return updates


def track_scope(experiment: dict) -> str | None:
    """Return the model a track-scoped experiment belongs to, or None if shared."""
    track = experiment.get("track_id")
    if not track or track == TRACK_DEFAULT:
        return None
    return track


def match_predictions_by_tag(
    experiments: list[dict],
    predictions: list[dict],
    tag_key: str,
    date_key: str = "target_date",
    model_key: str = "model_name",
) -> dict[str, list[dict]]:
    """Attribute evaluated predictions to each experiment.

    Exact prompt tag wins. When a variant has no tagged rows (older rows were
    written before the tag column was populated), fall back to its evaluation
    window, scoped to the experiment's model track so one model's predictions
    cannot score another model's prompt.
    """
    ranked = [p for p in predictions if not is_backtest_tag(p.get(tag_key))]
    by_tag: dict[str, list[dict]] = defaultdict(list)
    for prediction in ranked:
        tag = prediction.get(tag_key)
        if tag:
            by_tag[tag].append(prediction)

    matched: dict[str, list[dict]] = {}
    for experiment in experiments:
        tag = experiment["variant_tag"]
        rows = by_tag.get(tag)
        if not rows:
            start = as_date(experiment.get("week_start"))
            end = as_date(experiment.get("week_end"))
            track = track_scope(experiment)
            if start and end:
                rows = [
                    p
                    for p in ranked
                    if (target := as_date(p.get(date_key))) is not None
                    and start <= target <= end
                    and (track is None or p.get(model_key) == track)
                ]
        matched[tag] = rows or []
    return matched


def recompute_experiment_metrics(
    experiments: list[dict],
    predictions: list[dict],
    tag_key: str,
    calculator,
) -> list[dict]:
    """Recompute metrics for each non-backtest experiment that still has evidence."""
    matched = match_predictions_by_tag(experiments, predictions, tag_key)
    report: list[dict] = []

    for experiment in experiments:
        if experiment.get("is_backtest"):
            continue
        tag = experiment["variant_tag"]
        if is_backtest_tag(tag):
            continue

        rows = matched.get(tag, [])
        metrics = calculator(rows) if rows else None
        report.append(
            {
                "id": experiment["id"],
                "variant_tag": tag,
                "track_id": experiment.get("track_id") or TRACK_DEFAULT,
                "status": experiment.get("status"),
                "created_at": experiment.get("created_at"),
                "old_score": (experiment.get("metrics") or {}).get("score"),
                "new_metrics": metrics,
                "prediction_count": len(rows),
            }
        )
    return report


def _latest(items: list[dict]) -> dict | None:
    if not items:
        return None
    return max(items, key=lambda item: str(item.get("created_at") or ""))


def propose_track_realignment(report: list[dict]) -> list[dict[str, Any]]:
    """Propose status and parent updates so each track's baseline is credible.

    The winner per track is chosen through ``select_baseline_candidate``: it skips
    the active variant (the ratchet compares against *other* variants) and applies
    the minimum-sample and shrinkage guards.

    Returns one proposal per experiment, carrying its recomputed metrics so callers
    can write metrics and status in a single update. ``status`` and ``parent_tag``
    are ``None`` when no change is required.
    """
    tracks: dict[str, list[dict]] = defaultdict(list)
    for item in report:
        tracks[item.get("track_id") or TRACK_DEFAULT].append(item)

    proposals: list[dict[str, Any]] = []
    for track, items in tracks.items():
        active = _latest([item for item in items if item.get("status") == "active"])
        variants = [{"variant_tag": item["variant_tag"], "metrics": item.get("new_metrics")} for item in items]
        best = select_baseline_candidate(variants, exclude_tag=active["variant_tag"] if active else None)
        baseline_tag = best[1]["variant_tag"] if best else None

        for item in items:
            status = None
            parent_tag = None
            if baseline_tag:
                if item["variant_tag"] == baseline_tag:
                    status = "baseline"
                elif item.get("status") == "baseline":
                    status = "saved"
                if active and item["id"] == active["id"]:
                    parent_tag = baseline_tag

            proposals.append(
                {
                    "id": item["id"],
                    "variant_tag": item["variant_tag"],
                    "track_id": track,
                    "metrics": item.get("new_metrics"),
                    "status": status,
                    "parent_tag": parent_tag,
                    "baseline_score": best[0] if best else None,
                }
            )
    return proposals


def summarize_tracks(proposals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Condense proposals into a per-track baseline summary."""
    summary: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        track = proposal["track_id"]
        entry = summary.setdefault(
            track,
            {"baseline_tag": None, "baseline_score": None, "active_tag": None},
        )
        if proposal["status"] == "baseline":
            entry["baseline_tag"] = proposal["variant_tag"]
            entry["baseline_score"] = proposal["baseline_score"]
        if proposal["parent_tag"] and proposal["status"] is None:
            entry["active_tag"] = proposal["variant_tag"]
    return summary
