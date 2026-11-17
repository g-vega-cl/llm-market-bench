#!/usr/bin/env python3
"""Team health forensics: bus factor, commit velocity, and crisis cadence.

Companion to ``hotspots.py``. Where the hotspot analyzer answers "which code is
fragile", this answers "is the team healthy": who writes the code, whether the
project is accelerating or stalling, and how often the team is firefighting.

The analyzer reads one scoped ``git log`` pass (plus one all-time author pass),
so its commit population matches the hotspot report it is embedded in.
"""

from __future__ import annotations

import math
import re
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

UNIT_SEPARATOR = "\x1f"
RECORD_PREFIX = "COMMIT" + UNIT_SEPARATOR
# hash, subject, author name, author email, author month. \x1f keeps subjects with
# colons or ":::" from breaking the parse.
RECORD_FORMAT = f"--format={RECORD_PREFIX}%h{UNIT_SEPARATOR}%s{UNIT_SEPARATOR}%an{UNIT_SEPARATOR}%ae{UNIT_SEPARATOR}%ad"

CRISIS_REGEX = re.compile(r"\b(revert|hotfix|emergency|rollback)\b", re.IGNORECASE)
CRISIS_LEADING_REGEX = re.compile(r"^(revert|hotfix|emergency|rollback)[!:.]?$", re.IGNORECASE)
BOT_REGEX = re.compile(r"\[bot\]|^(github-actions|actions-user|dependabot|renovate|greenkeeper)", re.IGNORECASE)
BOT_EMAIL_REGEX = re.compile(r"\[bot\]|^(actions|github-actions|actions-user)@github\.com$", re.IGNORECASE)
COMMIT_PREFIX_REGEX = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?!?:\s*(?P<desc>.*)$", re.IGNORECASE)
RELATIVE_WINDOW_REGEX = re.compile(r"^(?P<count>\d+)\s+(?P<unit>day|week|month|year)s?\s+ago$", re.IGNORECASE)
DAYS_PER_MONTH = 30.44

# Types whose description mentions firefighting without being a firefight:
# "docs: rollback procedure" documents a crisis, it is not one.
INFORMATIONAL_TYPES = frozenset({"docs", "doc", "test", "tests", "style", "chore", "build", "ci"})
# Feature commits describe what the code will do ("feat: rollback support"), not
# what the team is doing right now, so their leading word is not a crisis signal.
NON_CRISIS_LEADING_TYPES = INFORMATIONAL_TYPES | {"feat", "feature", "refactor", "perf"}

BUS_FACTOR_THRESHOLD = 0.60
VELOCITY_TREND_BAND = 0.25
VELOCITY_TREND_MIN_MONTHS = 6
DEFAULT_VELOCITY_MONTHS = 12
# Crisis commits per month: <= 0.5 is normal, > 1.0 means constant firefighting.
CRISIS_STABLE_RATE = 0.5
CRISIS_ELEVATED_RATE = 1.0
INACTIVE_MIN_COMMITS = 3


@dataclass
class TeamCommit:
    commit_hash: str
    subject: str
    author: str
    email: str
    month: str

    @property
    def identity(self) -> str:
        """Stable author key: one human may commit under several display names."""
        return (self.email or self.author).strip().lower() or "unknown"

    @property
    def display_name(self) -> str:
        return self.author.strip() or "unknown"


@dataclass
class AuthorMetric:
    name: str
    identity: str
    commits: int
    share: float
    is_bot: bool


@dataclass
class VelocityMonth:
    month: str
    commits: int


@dataclass
class CrisisEvent:
    commit_hash: str
    subject: str
    kind: str


@dataclass
class TeamReport:
    since: str
    total_commits: int
    authors: list[AuthorMetric]
    bus_factor: float
    bus_factor_author: str | None
    concentration: str
    velocity: list[VelocityMonth]
    velocity_trend: str
    crisis_events: list[CrisisEvent]
    crisis_status: str
    window_months: int = 1
    window_months_source: str = "since"
    inactive_authors: list[str] = field(default_factory=list)
    velocity_window: str = "12 months ago"

    def to_dict(self) -> dict:
        return asdict(self)


def _run_git(args: list[str]) -> str:
    res = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return res.stdout


def is_bot_author(name: str, email: str = "") -> bool:
    return bool(BOT_REGEX.search(name)) or bool(BOT_EMAIL_REGEX.search(email))


def to_team_commits(records: list[object]) -> list[TeamCommit]:
    """Adapt hotspot ``CommitRecord`` objects into team commits (structural typing)."""
    return [
        TeamCommit(
            commit_hash=str(getattr(r, "commit_hash", "")),
            subject=str(getattr(r, "subject", "")),
            author=str(getattr(r, "author", "")),
            email=str(getattr(r, "email", "")),
            month=str(getattr(r, "month", "")),
        )
        for r in records
    ]


def parse_team_log(raw_log: str) -> list[TeamCommit]:
    commits: list[TeamCommit] = []
    for line in raw_log.splitlines():
        line = line.strip()
        if not line.startswith(RECORD_PREFIX):
            continue  # --name-only paths and blank lines are irrelevant to team metrics
        parts = line[len(RECORD_PREFIX) :].split(UNIT_SEPARATOR)
        if len(parts) < 5:
            continue
        commit_hash, subject, author, email, month = parts[:5]
        commits.append(
            TeamCommit(
                commit_hash=commit_hash.strip(),
                subject=subject.strip(),
                author=author.strip(),
                email=email.strip(),
                month=month.strip(),
            )
        )
    return commits


def count_authors(commits: list[TeamCommit]) -> list[AuthorMetric]:
    """Group commits by author identity (email), keeping the most-used display name."""
    if not commits:
        return []

    names: dict[str, Counter[str]] = {}
    counts: Counter[str] = Counter()
    for commit in commits:
        key = commit.identity
        counts[key] += 1
        names.setdefault(key, Counter())[commit.display_name] += 1

    total = sum(counts.values())
    authors: list[AuthorMetric] = []
    for key, count in counts.items():
        name = names[key].most_common(1)[0][0]
        authors.append(
            AuthorMetric(
                name=name,
                identity=key,
                commits=count,
                share=count / total,
                is_bot=is_bot_author(name, key),
            )
        )
    authors.sort(key=lambda a: (-a.commits, a.name))
    return authors


def assess_bus_factor(authors: list[AuthorMetric]) -> tuple[str | None, float, str]:
    """Return (top human author, its share of human commits, concentration label)."""
    humans = [a for a in authors if not a.is_bot]
    human_commits = sum(a.commits for a in humans)
    if not humans or human_commits == 0:
        return None, 0.0, "UNKNOWN"

    top = max(humans, key=lambda a: a.commits)
    share = top.commits / human_commits
    concentration = "FRAGILE" if share >= BUS_FACTOR_THRESHOLD else "BALANCED"
    return top.name, share, concentration


def _month_range(start: str, end: str) -> list[str]:
    start_year, start_month = (int(part) for part in start.split("-")[:2])
    end_year, end_month = (int(part) for part in end.split("-")[:2])

    months: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return months


def month_of(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def shift_month(month: str, delta: int) -> str:
    year, mon = (int(part) for part in month.split("-")[:2])
    index = year * 12 + (mon - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def build_velocity_series(
    month_tokens: list[str],
    through: str | None = None,
    start: str | None = None,
) -> list[VelocityMonth]:
    """Group commits by YYYY-MM and zero-fill idle months, including trailing ones.

    ``start`` anchors the series to the requested window (so a quiet project shows
    its idle months); ``through`` only extends it forward — an earlier value never
    prepends leading zeros.
    """
    tokens = [token.strip() for token in month_tokens if token.strip()]
    if not tokens and not through and not start:
        return []

    candidates = tokens or [value for value in (start, through) if value]
    if not candidates:
        return []

    # A requested window start wins: commits authored just before it would
    # otherwise widen the series to 13 rows for a 12-month window.
    series_start = start or min(candidates)
    series_end = max(candidates)
    if through and through > series_end:
        series_end = through
    if not series_start or not series_end:
        return []

    counts = Counter(tokens)
    return [
        VelocityMonth(month=month, commits=counts.get(month, 0)) for month in _month_range(series_start, series_end)
    ]


def assess_velocity_trend(velocity: list[VelocityMonth]) -> str:
    if len(velocity) < VELOCITY_TREND_MIN_MONTHS:
        return "INSUFFICIENT"

    recent = sum(m.commits for m in velocity[-3:])
    prior = sum(m.commits for m in velocity[-6:-3])
    if prior == 0:
        return "ACCELERATING" if recent > 0 else "STEADY"

    ratio = recent / prior
    if ratio >= 1 + VELOCITY_TREND_BAND:
        return "ACCELERATING"
    if ratio <= 1 - VELOCITY_TREND_BAND:
        return "DECELERATING"
    return "STEADY"


def _crisis_kind(subject: str) -> str | None:
    """Detect firefighting intent, not incidental keyword mentions.

    ``fix(newsletter): eliminate date rollback`` fixes a rollback bug,
    ``docs: rollback procedure`` documents one, and ``feat: rollback-safe
    migrations`` is a feature — none is a crisis response. Only the commit
    type/scope or the leading description word counts.
    """
    match = COMMIT_PREFIX_REGEX.match(subject.strip())
    if match:
        commit_type = match.group("type").lower()
        # Informational and feature commits never signal firefighting, whatever the
        # scope or leading word says: "docs(rollback):", "feat(rollback):".
        if commit_type in NON_CRISIS_LEADING_TYPES:
            return None
        type_hit = CRISIS_REGEX.search(commit_type)
        if type_hit:
            return type_hit.group(1).lower()
        description = match.group("desc").strip()
    else:
        description = subject.strip()

    leading_word = description.split()[0] if description.split() else ""
    lead_hit = CRISIS_LEADING_REGEX.match(leading_word)
    return lead_hit.group(1).lower() if lead_hit else None


def parse_crisis_commits(commits: list[TeamCommit]) -> list[CrisisEvent]:
    events: list[CrisisEvent] = []
    for commit in commits:
        kind = _crisis_kind(commit.subject)
        if kind is None:
            continue
        events.append(CrisisEvent(commit_hash=commit.commit_hash, subject=commit.subject, kind=kind))
    return events


def assess_crisis_cadence(events: list[CrisisEvent], months: int) -> str:
    rate = len(events) / max(months, 1)
    if rate > CRISIS_ELEVATED_RATE:
        return "ELEVATED"
    if rate > CRISIS_STABLE_RATE:
        return "WATCH"
    return "STABLE"


def parse_author_log(raw_log: str) -> list[tuple[str, str]]:
    """Parse ``name<US>email`` pairs from the all-time author log."""
    pairs: list[tuple[str, str]] = []
    for line in raw_log.splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, email = line.partition(UNIT_SEPARATOR)
        pairs.append((name.strip(), email.strip()))
    return pairs


def inactive_contributors(
    all_time: list[tuple[str, str]],
    active_identities: set[str],
    min_commits: int = INACTIVE_MIN_COMMITS,
) -> list[str]:
    counts: Counter[str] = Counter()
    names: dict[str, Counter[str]] = {}
    for name, email in all_time:
        key = (email or name).strip().lower()
        counts[key] += 1
        names.setdefault(key, Counter())[name] += 1

    inactive = []
    for key, commits in counts.items():
        name = names[key].most_common(1)[0][0]
        if commits < min_commits or key in active_identities or is_bot_author(name, key):
            continue
        inactive.append(name)
    inactive.sort()
    return inactive


def window_months_for(since: str, today: date | None = None) -> int | None:
    """Resolve the requested window length in months, or None when unparseable.

    Git accepts free-form dates ("90 days ago", "2026-01-01"), so the common forms
    are resolved here and anything else falls back to the observed commit span.
    """
    today = today or date.today()
    relative = RELATIVE_WINDOW_REGEX.match(since.strip())
    if relative:
        count = int(relative.group("count"))
        unit = relative.group("unit").lower()
        days = count * {"day": 1, "week": 7, "month": DAYS_PER_MONTH, "year": 365.25}[unit]
        return max(1, math.ceil(days / DAYS_PER_MONTH))

    try:
        start = date.fromisoformat(since.strip())
    except ValueError:
        return None

    elapsed = (today.year - start.year) * 12 + (today.month - start.month) + 1
    return max(1, elapsed)


def build_team_report(
    commits: list[TeamCommit],
    all_time_authors: list[tuple[str, str]],
    since: str,
    velocity_window: str = "12 months ago",
    today: date | None = None,
    velocity_months: list[str] | None = None,
    window_months: int | None = None,
    velocity_start: str | None = None,
) -> TeamReport:
    """Pure core: derive the report from parsed commits (no I/O)."""
    today = today or date.today()
    authors = count_authors(commits)
    bus_author, bus_share, concentration = assess_bus_factor(authors)

    current_month = month_of(today)
    observed_span = build_velocity_series([c.month for c in commits], through=current_month) if commits else []
    requested = window_months or window_months_for(since, today)
    if requested:
        months, months_source = requested, "since"
    elif observed_span:
        months, months_source = len(observed_span), "observed"
    else:
        months, months_source = 1, "default"

    velocity = build_velocity_series(
        velocity_months if velocity_months is not None else [c.month for c in commits],
        through=current_month,
        start=velocity_start,
    )
    crisis_events = parse_crisis_commits(commits)

    return TeamReport(
        since=since,
        total_commits=len(commits),
        authors=authors,
        bus_factor=bus_share,
        bus_factor_author=bus_author,
        concentration=concentration,
        velocity=velocity,
        velocity_trend=assess_velocity_trend(velocity),
        crisis_events=crisis_events,
        crisis_status=assess_crisis_cadence(crisis_events, months),
        window_months=months,
        window_months_source=months_source,
        inactive_authors=inactive_contributors(all_time_authors, {a.identity for a in authors}),
        velocity_window=velocity_window,
    )


def _scoped_pathspec(scopes: list[str] | None) -> list[str]:
    return ["--", *scopes] if scopes else []


def fetch_velocity_months(velocity_window: str = "12 months ago", scopes: list[str] | None = None) -> list[str]:
    raw = _run_git(
        [
            "log",
            f"--since={velocity_window}",
            "--no-merges",
            "--format=%ad",
            "--date=format:%Y-%m",
            *_scoped_pathspec(scopes),
        ]
    )
    return raw.splitlines()


def fetch_all_time_authors(scopes: list[str] | None = None) -> list[tuple[str, str]]:
    raw = _run_git(["log", "--no-merges", f"--format=%an{UNIT_SEPARATOR}%ae", *_scoped_pathspec(scopes)])
    return parse_author_log(raw)


def analyze_team_from_commits(
    commits: list[TeamCommit],
    since: str = "90 days ago",
    scopes: list[str] | None = None,
    velocity_window: str = "12 months ago",
    today: date | None = None,
) -> TeamReport:
    """Team metrics for an already-parsed commit population (enforces parity)."""
    today = today or date.today()
    velocity_months = window_months_for(velocity_window, today) or DEFAULT_VELOCITY_MONTHS
    velocity_start = shift_month(month_of(today), -(velocity_months - 1))

    return build_team_report(
        commits,
        fetch_all_time_authors(scopes),
        since=since,
        velocity_window=velocity_window,
        today=today,
        velocity_months=fetch_velocity_months(velocity_window, scopes),
        velocity_start=velocity_start,
    )


def analyze_team(
    since: str = "90 days ago",
    scopes: list[str] | None = None,
    velocity_window: str = "12 months ago",
    today: date | None = None,
) -> TeamReport:
    """Standalone entry point: fetch the window itself, then analyze."""
    raw = _run_git(
        [
            "log",
            f"--since={since}",
            "--no-merges",
            RECORD_FORMAT,
            "--date=format:%Y-%m",
            *_scoped_pathspec(scopes),
        ]
    )
    return analyze_team_from_commits(parse_team_log(raw), since, scopes, velocity_window, today)


def _sparkline(commits: int, peak: int) -> str:
    if commits <= 0 or peak <= 0:
        return "·"
    width = max(1, round(commits / peak * 8))
    return "▇" * width


def _months_label(report: TeamReport) -> str:
    if report.window_months_source == "since":
        return str(report.window_months)
    if report.window_months_source == "observed":
        return f"{report.window_months} (estimated from commits)"
    return f"{report.window_months} (assumed)"


def format_team_terminal(report: TeamReport) -> str:
    if report.bus_factor_author is None:
        bus_line = f"Bus factor: no human commits in the window ({report.total_commits} commits) — UNKNOWN"
    else:
        bus_line = (
            f"Bus factor: {report.bus_factor_author} carries "
            f"{report.bus_factor * 100:.0f}% of human commits — {report.concentration}"
        )

    lines = [
        f"━━━ Team Health (Window: {report.since}, Months: {_months_label(report)}, Commits: {report.total_commits}) ━━━",
        bus_line,
    ]

    if report.inactive_authors:
        lines.append(
            f"Inactive this window (all-time contributors with no commits): {', '.join(report.inactive_authors)}"
        )

    if report.authors:
        lines.append("")
        lines.append(f"{'Author':<30} {'Commits':>8} {'Share':>8}")
        lines.append("─" * 48)
        for author in report.authors[:8]:
            name = author.name if len(author.name) <= 29 else author.name[:28] + "…"
            lines.append(f"{name:<30} {author.commits:>8} {author.share * 100:>7.1f}%")

    if report.velocity:
        peak = max(m.commits for m in report.velocity)
        lines.append("")
        lines.append(f"Commit velocity by month, {report.velocity_window} ({report.velocity_trend}):")
        for month in report.velocity[-12:]:
            lines.append(f"  {month.month}  {month.commits:>4}  {_sparkline(month.commits, peak)}")

    lines.append("")
    lines.append(
        f"Crisis cadence: {len(report.crisis_events)} revert/hotfix/emergency/rollback — {report.crisis_status}"
    )
    for event in report.crisis_events[:10]:
        lines.append(f"  {event.commit_hash}  [{event.kind}] {event.subject}")

    return "\n".join(lines)


def format_team_markdown(report: TeamReport) -> str:
    if report.bus_factor_author is None:
        bus_line = "- **Bus factor**: no human commits in the window — **UNKNOWN**."
    else:
        bus_line = (
            f"- **Bus factor**: `{report.bus_factor_author}` accounts for "
            f"**{report.bus_factor * 100:.0f}%** of human commits — **{report.concentration}** "
            f"(single-author risk when ≥ {BUS_FACTOR_THRESHOLD * 100:.0f}%)."
        )

    md = [
        "",
        "## Team Health",
        "",
        f"Team forensics over the same scoped window (commits analyzed: **{report.total_commits}**, "
        f"months: **{_months_label(report)}**).",
        "",
        bus_line,
        f"- **Commit velocity trend** ({report.velocity_window}): **{report.velocity_trend}** "
        f"(last 3 months vs the 3 before, ±{VELOCITY_TREND_BAND * 100:.0f}% band).",
        f"- **Crisis cadence**: {len(report.crisis_events)} revert/hotfix/emergency/rollback "
        f"commits in {report.window_months} month(s) — **{report.crisis_status}**.",
    ]

    if report.inactive_authors:
        names = ", ".join(f"`{name}`" for name in report.inactive_authors)
        md.append(f"- **Inactive this window**: {names} (no commits in the window).")

    if report.authors:
        md.extend(
            [
                "",
                "### Contributors",
                "",
                "| Author | Commits | Share of window commits |",
                "| :--- | ---: | ---: |",
            ]
        )
        for author in report.authors[:10]:
            md.append(f"| `{author.name}` | {author.commits} | {author.share * 100:.1f}% |")

    if report.velocity:
        peak = max(m.commits for m in report.velocity)
        md.extend(
            [
                "",
                "### Commit Velocity",
                "",
                "| Month | Commits | Trend |",
                "| :--- | ---: | :--- |",
            ]
        )
        for month in report.velocity[-12:]:
            md.append(f"| {month.month} | {month.commits} | {_sparkline(month.commits, peak)} |")

    md.extend(["", "### Crisis Cadence", ""])
    if report.crisis_events:
        md.extend(["| Commit | Kind | Subject |", "| :--- | :--- | :--- |"])
        for event in report.crisis_events[:10]:
            md.append(f"| `{event.commit_hash}` | {event.kind} | {event.subject} |")
    else:
        md.append("No revert, hotfix, emergency, or rollback commits in the window.")

    return "\n".join(md)
