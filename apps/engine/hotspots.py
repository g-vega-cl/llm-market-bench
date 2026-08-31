#!/usr/bin/env python3
"""Code Hotspot and Churn Forensics Analyzer.

Calculates code churn, bug fix density, hotspot risk scores, and temporal
coupling (co-churn) across the git history.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIKI_FILE = REPO_ROOT / "wiki" / "concepts" / "code-hotspots.md"

EXCLUDED_PATTERNS = [
    re.compile(r"\.gen\.[a-z0-9]+$"),  # routeTree.gen.ts, etc.
    re.compile(r"lock\.(json|yaml)$"),  # package-lock.json, pnpm-lock.yaml
    re.compile(r"\.lock$"),  # poetry.lock
    re.compile(r"(^|/)\.venv/"),
    re.compile(r"(^|/)venv/"),
    re.compile(r"(^|/)\.agents/"),
    re.compile(r"(^|/)\.gemini/"),
    re.compile(r"(^|/)\.husky/"),
    re.compile(r"(^|/)\.system_generated/"),
    re.compile(r"(^|/)wiki/"),
    re.compile(r"(^|/)raw/"),
    re.compile(r"^supabase/migrations/"),
]

BUG_REGEX = re.compile(r"\b(fix|fixed|fixes|bug|bugs|broken|patch|patched|hotfix|defect)\b", re.IGNORECASE)


@dataclass
class CommitRecord:
    commit_hash: str
    subject: str
    is_fix: bool
    files: list[str]


@dataclass
class HotspotMetric:
    path: str
    churn: int
    bug_fixes: int
    fix_ratio: float
    loc: int
    score: float
    risk_level: str


@dataclass
class CouplingMetric:
    file_a: str
    file_b: str
    co_commits: int
    ratio_a: float
    ratio_b: float


@dataclass
class HotspotReport:
    since: str
    total_commits: int
    hotspots: list[HotspotMetric]
    couplings: list[CouplingMetric]

    def to_json(self) -> str:
        return json.dumps(
            {
                "since": self.since,
                "total_commits": self.total_commits,
                "hotspots": [asdict(h) for h in self.hotspots],
                "couplings": [asdict(c) for c in self.couplings],
            },
            indent=2,
        )


def is_excluded_path(path: str) -> bool:
    clean_path = path.strip()
    if not clean_path:
        return True
    return any(pattern.search(clean_path) for pattern in EXCLUDED_PATTERNS)


def is_bug_fix_commit(subject: str) -> bool:
    return bool(BUG_REGEX.search(subject))


def run_git_log(since: str, scopes: list[str] | None = None) -> str:
    cmd = [
        "git",
        "log",
        f"--since={since}",
        "--name-only",
        "--format=COMMIT:%h:::%s",
    ]
    if scopes:
        cmd.append("--")
        cmd.extend(scopes)

    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return res.stdout


def parse_git_log(log_output: str) -> list[CommitRecord]:
    commits: list[CommitRecord] = []
    current_hash: str | None = None
    current_subject: str = ""
    current_files: list[str] = []

    for line in log_output.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("COMMIT:"):
            if current_hash is not None:
                commits.append(
                    CommitRecord(
                        commit_hash=current_hash,
                        subject=current_subject,
                        is_fix=is_bug_fix_commit(current_subject),
                        files=current_files,
                    )
                )
                current_files = []

            meta = line[len("COMMIT:") :]
            parts = meta.split(":::", 1)
            current_hash = parts[0]
            current_subject = parts[1] if len(parts) > 1 else ""
        else:
            if not is_excluded_path(line):
                current_files.append(line)

    if current_hash is not None:
        commits.append(
            CommitRecord(
                commit_hash=current_hash,
                subject=current_subject,
                is_fix=is_bug_fix_commit(current_subject),
                files=current_files,
            )
        )

    return commits


def get_file_loc(rel_path: str) -> int:
    full_path = REPO_ROOT / rel_path
    if not full_path.is_file():
        return 0
    try:
        with open(full_path, encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def determine_risk_level(score: float, churn: int, fix_ratio: float) -> str:
    if score >= 100 or (churn >= 15 and fix_ratio >= 0.35):
        return "CRITICAL"
    if score >= 30 or (churn >= 10 and fix_ratio >= 0.25):
        return "HIGH"
    if score >= 10 or churn >= 10:
        return "MEDIUM"
    return "LOW"


def calculate_hotspots(commits: list[CommitRecord], top_n: int | None = None) -> list[HotspotMetric]:
    churn_counts: dict[str, int] = defaultdict(int)
    fix_counts: dict[str, int] = defaultdict(int)

    for commit in commits:
        unique_files = set(commit.files)
        for f in unique_files:
            churn_counts[f] += 1
            if commit.is_fix:
                fix_counts[f] += 1

    metrics: list[HotspotMetric] = []
    for file_path, churn in churn_counts.items():
        bug_fixes = fix_counts[file_path]
        fix_ratio = bug_fixes / churn if churn > 0 else 0.0
        score = float(churn * bug_fixes)
        loc = get_file_loc(file_path)
        risk = determine_risk_level(score, churn, fix_ratio)

        metrics.append(
            HotspotMetric(
                path=file_path,
                churn=churn,
                bug_fixes=bug_fixes,
                fix_ratio=fix_ratio,
                loc=loc,
                score=score,
                risk_level=risk,
            )
        )

    # Sort primarily by score descending, then by churn descending
    metrics.sort(key=lambda m: (m.score, m.churn, m.bug_fixes), reverse=True)

    if top_n is not None:
        return metrics[:top_n]
    return metrics


def calculate_coupling(
    commits: list[CommitRecord],
    min_co_commits: int = 3,
    min_ratio: float = 0.25,
    max_commit_files: int = 15,
) -> list[CouplingMetric]:
    file_churn: dict[str, int] = defaultdict(int)
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)

    for commit in commits:
        unique_files = sorted(set(commit.files))
        for f in unique_files:
            file_churn[f] += 1

        # Skip commits touching too many files (e.g. bulk formatting or refactoring)
        if len(unique_files) > max_commit_files:
            continue

        for i in range(len(unique_files)):
            for j in range(i + 1, len(unique_files)):
                pair = (unique_files[i], unique_files[j])
                pair_counts[pair] += 1

    couplings: list[CouplingMetric] = []
    for (file_a, file_b), count in pair_counts.items():
        if count < min_co_commits:
            continue

        churn_a = file_churn[file_a]
        churn_b = file_churn[file_b]
        if churn_a == 0 or churn_b == 0:
            continue

        ratio_a = count / churn_a
        ratio_b = count / churn_b

        if ratio_a >= min_ratio or ratio_b >= min_ratio:
            couplings.append(
                CouplingMetric(
                    file_a=file_a,
                    file_b=file_b,
                    co_commits=count,
                    ratio_a=ratio_a,
                    ratio_b=ratio_b,
                )
            )

    couplings.sort(key=lambda c: (c.co_commits, max(c.ratio_a, c.ratio_b)), reverse=True)
    return couplings


def analyze_hotspots(
    since: str = "90 days ago",
    scopes: list[str] | None = None,
    top_n: int = 20,
) -> HotspotReport:
    if scopes is None:
        scopes = ["apps/", "packages/"]

    raw_log = run_git_log(since=since, scopes=scopes)
    commits = parse_git_log(raw_log)
    hotspots = calculate_hotspots(commits, top_n=top_n)
    couplings = calculate_coupling(commits)

    return HotspotReport(
        since=since,
        total_commits=len(commits),
        hotspots=hotspots,
        couplings=couplings,
    )


def format_terminal_table(report: HotspotReport) -> str:
    lines = [
        f"Code Hotspots & Churn Forensics (Window: {report.since}, Commits: {report.total_commits})",
        "─" * 90,
        f"{'File':<46} {'Churn':>6} {'Fixes':>6} {'Fix Ratio':>10} {'LOC':>6} {'Score':>7} {'Risk':>9}",
        "─" * 90,
    ]

    for h in report.hotspots:
        ratio_str = f"{h.fix_ratio * 100:.1f}%"
        # Truncate long paths cleanly
        path_str = h.path if len(h.path) <= 45 else "…" + h.path[-44:]
        lines.append(
            f"{path_str:<46} {h.churn:>6} {h.bug_fixes:>6} {ratio_str:>10} {h.loc:>6} {h.score:>7.0f} {h.risk_level:>9}"
        )

    lines.append("─" * 90)

    if report.couplings:
        lines.append("\nTop Temporal Couplings (Files changing together):")
        for c in report.couplings[:10]:
            lines.append(
                f"  • {c.file_a} <-> {c.file_b}\n"
                f"    {c.co_commits} shared commits ({c.ratio_a * 100:.0f}% of {Path(c.file_a).name}, {c.ratio_b * 100:.0f}% of {Path(c.file_b).name})"
            )

    return "\n".join(lines)


def format_markdown_report(report: HotspotReport) -> str:
    md = [
        "---",
        "tags: [architecture, code-quality, metrics]",
        "category: concept",
        "---",
        "",
        "# Code Hotspots & Architectural Friction",
        "",
        f"Living metrics generated from git history (Lookback window: **{report.since}**, Total commits analyzed: **{report.total_commits}**).",
        "",
        "## Top Hotspots",
        "",
        "Files with high churn and high bug fix density represent code where changes frequently cause regressions.",
        "",
        "| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for h in report.hotspots:
        ratio_str = f"{h.fix_ratio * 100:.1f}%"
        md.append(
            f"| `{h.path}` | {h.churn} | {h.bug_fixes} | {ratio_str} | {h.loc} | {h.score:.0f} | **{h.risk_level}** |"
        )

    if report.couplings:
        md.extend(
            [
                "",
                "## Temporal Coupling (Co-churn)",
                "",
                "Files that consistently change in the same commit indicate implicit architectural coupling.",
                "",
                "| Primary File | Coupled File | Shared Commits | Coupling Strength |",
                "| :--- | :--- | :---: | :---: |",
            ]
        )
        for c in report.couplings[:15]:
            max_ratio = max(c.ratio_a, c.ratio_b) * 100
            md.append(f"| `{c.file_a}` | `{c.file_b}` | {c.co_commits} | {max_ratio:.0f}% |")

    md.extend(
        [
            "",
            "## Usage Guidelines for LLM Agents",
            "",
            "When planning or modifying files listed in this report:",
            "1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.",
            "2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.",
            "3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.",
            "",
            "## Related",
            "* [[concepts/visual-planning]]",
            "* [[overview]]",
            "",
        ]
    )

    return "\n".join(md)


def _display_path(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze git churn, bug hotspots, and temporal coupling.")
    parser.add_argument(
        "--since",
        default="90 days ago",
        help="Git log lookback window (default: '90 days ago')",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top hotspots to report (default: 20)",
    )
    parser.add_argument(
        "--scope",
        nargs="*",
        default=["apps/", "packages/"],
        help="Subdirectories to scope git analysis to (default: apps/ packages/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results",
    )
    parser.add_argument(
        "--write-wiki",
        action="store_true",
        help=f"Write output markdown to wiki page: {_display_path(WIKI_FILE)}",
    )

    args = parser.parse_args()

    try:
        report = analyze_hotspots(since=args.since, scopes=args.scope, top_n=args.top)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Git command failed: {e}\n")
        return 1

    if args.json:
        print(report.to_json())
    else:
        print(format_terminal_table(report))

    if args.write_wiki:
        wiki_content = format_markdown_report(report)
        WIKI_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(WIKI_FILE, "w", encoding="utf-8") as f:
            f.write(wiki_content)
        print(f"\nUpdated wiki concept page: {_display_path(WIKI_FILE)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
