"""Terminal Scoreboard and Artifact Visualizer for Local Autoresearch."""

from __future__ import annotations

import contextlib
import os
from typing import Any


def render_terminal_dashboard(
    history: list[dict[str, Any]],
    current_baseline: dict[str, Any],
    latest_weekly_breakdown: dict[str, Any] | None = None,
) -> str:
    """Render a terminal-friendly ASCII scoreboard, weekly iteration breakdown, and progress chart."""
    lines: list[str] = [
        "",
        "╔════════════════════════════════════════════════════════════════════════════════════════════════╗",
        "║                           LOCAL AUTORESEARCH EXPERIMENT SCOREBOARD                             ║",
        "╠════╦═════════════════╦══════════╦══════════╦══════════╦══════════════╦════════════════════════╣",
        "║ It ║ Variant Tag     ║ Train %  ║ Test %   ║ Overfit  ║ Ratchet Scr  ║ Status                 ║",
        "╠════╬═════════════════╬══════════╬══════════╬══════════╬══════════════╬════════════════════════╣",
    ]

    for item in history:
        it = item.get("iteration", 0)
        tag = item.get("variant_tag", "unknown")[:15]
        train_p = item.get("train_score", 0.0)
        test_p = item.get("test_score", 0.0)
        overfit = item.get("overfit_penalty", 0.0)
        eff = item.get("effective_score", 0.0)
        is_winner = item.get("is_baseline_beat", False)
        status_reason = item.get("status_reason")
        status = "🏆 NEW BASELINE" if is_winner else "❌ DISCARDED"
        if status_reason == "vault_overfit":
            status = "🛡️ VAULT OVERFIT"
        if it == 0:
            status = "🟢 INITIAL BASE"

        lines.append(
            f"║ {it:<2} ║ {tag:<15} ║ {train_p:>7.2f}% ║ {test_p:>7.2f}% ║ {overfit:>7.2f}% ║ {eff:>11.2f}  ║ {status:<22} ║"
        )

    lines.extend(
        [
            "╚════╩═════════════════╩══════════╩══════════╩══════════╩══════════════╩════════════════════════╝",
            f" Current Best Baseline: {current_baseline.get('variant_tag', 'none')} "
            f"(Canonical Ratchet Score: {float(current_baseline.get('effective_score', 0.0)):.2f})",
            "",
        ]
    )

    if latest_weekly_breakdown:
        lines.append("--- Latest Weekly Iterations Breakdown ---")
        lines.append("┌───────────┬───────┬───────┬────────────┬───────────┬─────────┐")
        lines.append("│ Week      │ Split │ Days  │ Close Acc% │ Traded WR │ Score   │")
        lines.append("├───────────┼───────┼───────┼────────────┼───────────┼─────────┤")
        for w, w_info in sorted(latest_weekly_breakdown.items()):
            split_lbl = w_info.get("split", "TRAIN")
            days_c = w_info.get("days_count", 0)
            acc = w_info.get("accuracy_pct", 0.0)
            t_wr = w_info.get("traded_win_rate_pct", 0.0)
            sc = w_info.get("score", 0.0)
            lines.append(f"│ {w:<9} │ {split_lbl:<5} │ {days_c:>5} │ {acc:>9.1f}% │ {t_wr:>8.1f}% │ {sc:>7.2f} │")
        lines.append("└───────────┴───────┴───────┴────────────┴───────────┴─────────┘")
        lines.append("")

    # ASCII Bar chart
    lines.append("--- Ratchet Score Trajectory ---")
    for item in history:
        it = item.get("iteration", 0)
        tag = item.get("variant_tag", "unk")[:8]
        score = max(0.0, min(100.0, float(item.get("effective_score", 0.0))))
        bar_len = int(score / 2.5)  # 100 score = 40 chars
        bar = "█" * bar_len
        marker = "🏆" if item.get("is_baseline_beat") else "·"
        lines.append(f"It {it:<2} [{tag}] {marker} |{bar:<40}| {score:.2f}")

    lines.append("--------------------------------\n")
    return "\n".join(lines)


def update_dashboard_artifact(
    history: list[dict[str, Any]],
    current_baseline: dict[str, Any],
    artifact_path: str,
    latest_weekly_breakdown: dict[str, Any] | None = None,
) -> None:
    """Generate or update structured Markdown artifact with Mermaid score chart."""
    with contextlib.suppress(Exception):
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)

    rows = []
    for item in history:
        it = item.get("iteration", 0)
        tag = item.get("variant_tag", "unknown")
        train_p = item.get("train_score", 0.0)
        test_p = item.get("test_score", 0.0)
        eff = item.get("effective_score", 0.0)
        is_winner = item.get("is_baseline_beat", False)
        status_reason = item.get("status_reason")
        st = "🏆 Winner (New Baseline)" if is_winner else "Discarded"
        if status_reason == "vault_overfit":
            st = "🛡️ Overfit (Vault Rejected)"
        if it == 0:
            st = "Initial Clean-Sheet Baseline"
        hyp = item.get("hypothesis", "Clean start from 0")
        rows.append(f"| {it} | `{tag}` | {train_p:.2f}% | {test_p:.2f}% | **{eff:.2f}** | {st} | {hyp} |")

    table_md = "\n".join(rows)

    manifest_info = current_baseline.get("manifest", {})
    selected_news = manifest_info.get("selected_newsletters")
    news_str = ", ".join(selected_news) if selected_news else "All available"
    proxies_str = ", ".join(manifest_info.get("include_macro_proxies", []))

    weekly_md = ""
    if latest_weekly_breakdown:
        w_rows = []
        for w, w_info in sorted(latest_weekly_breakdown.items()):
            sp = w_info.get("split", "TRAIN")
            cnt = w_info.get("days_count", 0)
            acc = w_info.get("accuracy_pct", 0.0)
            t_wr = w_info.get("traded_win_rate_pct", 0.0)
            sc = w_info.get("score", 0.0)
            w_rows.append(f"| `{w}` | {sp} | {cnt} | {acc:.1f}% | {t_wr:.1f}% | **{sc:.2f}** |")
        weekly_md = (
            "\n\n---\n\n## 📅 Latest Weekly Iteration Breakdown\n\n"
            "| Week | Split | Days | Close Accuracy | Traded Win Rate | Ratchet Score |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n" + "\n".join(w_rows)
        )

    content = f"""# Local Autoresearch Session Report

> **Active Baseline**: `{current_baseline.get("variant_tag", "none")}`  
> **Canonical Ratchet Score**: `{float(current_baseline.get("effective_score", 0.0)):.2f}`  
> **Clean-Sheet Origin**: Started from 0 (Format blocks only)

---

## 📊 Iterations History

| Iteration | Variant Tag | Train Score | Test Score | Effective Score | Status | Hypothesis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{table_md}
{weekly_md}

---

## 🎯 Current Best Configuration

### Decision Criteria (Jev)
- **UP Criteria**:
  > {current_baseline.get("criteria_up", "N/A")}
- **DOWN Criteria**:
  > {current_baseline.get("criteria_down", "N/A")}
- **Confidence Gate**: `{current_baseline.get("min_confidence", 50.0)}%`

### Data Manifest ("Box of Data")
- **Curated Newsletters**: {news_str}
- **Macro Proxies**: {proxies_str}
- **Currency (UUP)**: `{"Included" if manifest_info.get("include_currency_uup") else "Pruned (Excluded)"}`
- **Options Derivatives**: `{"Included" if manifest_info.get("include_options_derivatives") else "Excluded"}`
- **Economic Calendar**: `{"Included" if manifest_info.get("include_economic_calendar") else "Excluded"}`

---

## 📈 Ratchet Progression

```mermaid
flowchart LR
    Start["Clean Start (0)"] --> Base["Baseline: {current_baseline.get("effective_score", 0.0):.2f}"]
    Base --> Loop["Local Qwen (Strata) Mutates Criteria + Data Manifest"]
    Loop --> Eval["Jev Evaluates 9 Weeks in Parallel (2.5s)"]
    Eval --> OverfitCheck["Overfit Check (Train vs Test Spread)"]
    OverfitCheck --> Decision{{"Beats Baseline?"}}
    Decision -- Yes --> NewBase["🏆 New Baseline Established"]
    Decision -- No --> Discard["❌ Discard & Learn Causal Lesson"]
```
"""

    with contextlib.suppress(Exception), open(artifact_path, "w", encoding="utf-8") as f:
        f.write(content)
