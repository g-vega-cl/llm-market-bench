from datetime import date
from unittest.mock import patch

from apps.engine.hotspot_team import (
    UNIT_SEPARATOR,
    AuthorMetric,
    CrisisEvent,
    TeamCommit,
    TeamReport,
    VelocityMonth,
    analyze_team,
    analyze_team_from_commits,
    assess_bus_factor,
    assess_crisis_cadence,
    assess_velocity_trend,
    build_team_report,
    build_velocity_series,
    count_authors,
    inactive_contributors,
    is_bot_author,
    parse_author_log,
    parse_crisis_commits,
    parse_team_log,
    to_team_commits,
    window_months_for,
)

TODAY = date(2026, 11, 17)


def _commit(
    subject: str,
    author: str = "alice",
    email: str = "alice@example.com",
    month: str = "2026-11",
    sha: str = "abc1234",
) -> TeamCommit:
    return TeamCommit(commit_hash=sha, subject=subject, author=author, email=email, month=month)


def _record(
    subject: str,
    author: str = "alice",
    email: str = "alice@example.com",
    month: str = "2026-11",
    sha: str = "abc1234",
) -> str:
    fields = UNIT_SEPARATOR.join([sha, subject, author, email, month])
    return f"COMMIT{UNIT_SEPARATOR}{fields}"


def test_is_bot_author():
    assert is_bot_author("google-labs-jules[bot]", "161369871+google-labs-jules[bot]@users.noreply.github.com")
    assert is_bot_author("dependabot[bot]", "dependabot[bot]@users.noreply.github.com")
    assert not is_bot_author("g-vega-cl", "g.vega.cl@gmail.com")
    # Two display names, one human: bots are detected on name or email only
    assert not is_bot_author("Cesar Vega", "g.vega.cl@gmail.com")


def test_parse_team_log_skips_name_only_paths_and_malformed_lines():
    raw = "\n".join(
        [
            _record("feat: add loader"),
            "apps/engine/core/config.py",
            "COMMIT" + UNIT_SEPARATOR + "broken-record",
            _record("fix: correct parsing", sha="def5678"),
        ]
    )
    commits = parse_team_log(raw)

    assert len(commits) == 2
    assert commits[0].commit_hash == "abc1234"
    assert commits[0].subject == "feat: add loader"
    assert commits[0].month == "2026-11"
    assert commits[1].commit_hash == "def5678"


def test_parse_team_log_tolerates_separators_in_subject():
    raw = _record("fix: handle a:::b separator without corruption")
    commits = parse_team_log(raw)

    assert commits[0].subject == "fix: handle a:::b separator without corruption"
    assert commits[0].month == "2026-11"


def test_count_authors_merges_identities_by_email():
    # Observed in this repo: one human commits under two display names with one email
    commits = [
        _commit("feat: a", author="g-vega-cl", email="g.vega.cl@gmail.com"),
        _commit("feat: b", author="g-vega-cl", email="g.vega.cl@gmail.com"),
        _commit("feat: c", author="Cesar Vega", email="g.vega.cl@gmail.com"),
        _commit("feat: d", author="bob", email="bob@example.com"),
    ]
    authors = count_authors(commits)

    assert len(authors) == 2
    assert authors[0].name == "g-vega-cl"  # most-used display name wins
    assert authors[0].identity == "g.vega.cl@gmail.com"
    assert authors[0].commits == 3
    assert round(authors[0].share, 3) == 0.75
    assert authors[1].share == 0.25


def test_count_authors_empty():
    assert count_authors([]) == []


def test_assess_bus_factor_fragile():
    commits = [_commit("c", email="a@x.com")] * 4 + [_commit("c", author="bob", email="b@x.com")]
    name, share, concentration = assess_bus_factor(count_authors(commits))

    assert name == "alice"
    assert round(share, 3) == 0.8
    assert concentration == "FRAGILE"


def test_assess_bus_factor_balanced():
    commits = (
        [_commit("c", email="a@x.com")] * 2
        + [_commit("c", author="bob", email="b@x.com")] * 2
        + [_commit("c", author="carol", email="c@x.com")]
    )
    name, share, concentration = assess_bus_factor(count_authors(commits))

    assert name == "alice"
    assert share == 0.4
    assert concentration == "BALANCED"


def test_assess_bus_factor_excludes_bots_from_denominator():
    commits = [
        _commit("c", email="a@x.com"),
        _commit("c", email="a@x.com"),
        _commit("c", author="bob", email="b@x.com"),
        _commit("c", author="renovate[bot]", email="bot@x.com"),
        _commit("c", author="renovate[bot]", email="bot@x.com"),
        _commit("c", author="renovate[bot]", email="bot@x.com"),
    ]
    name, share, concentration = assess_bus_factor(count_authors(commits))

    assert name == "alice"
    # Bots are excluded from the denominator: 2 of 3 human commits is single-author risk
    assert round(share, 3) == round(2 / 3, 3)
    assert concentration == "FRAGILE"


def test_assess_bus_factor_all_bots_is_unknown():
    commits = [_commit("c", author="renovate[bot]", email="bot@x.com")] * 3
    assert assess_bus_factor(count_authors(commits)) == (None, 0.0, "UNKNOWN")
    assert assess_bus_factor([]) == (None, 0.0, "UNKNOWN")


def test_build_velocity_series_fills_interior_gaps():
    series = build_velocity_series(["2026-01", "2026-01", "2026-04"])

    assert series == [
        VelocityMonth("2026-01", 2),
        VelocityMonth("2026-02", 0),
        VelocityMonth("2026-03", 0),
        VelocityMonth("2026-04", 1),
    ]


def test_build_velocity_series_crosses_year_boundary():
    series = build_velocity_series(["2025-11", "2026-01"])

    assert series == [
        VelocityMonth("2025-11", 1),
        VelocityMonth("2025-12", 0),
        VelocityMonth("2026-01", 1),
    ]


def test_build_velocity_series_zero_fills_trailing_months():
    series = build_velocity_series(["2026-09", "2026-09"], through="2026-11")

    assert series == [
        VelocityMonth("2026-09", 2),
        VelocityMonth("2026-10", 0),
        VelocityMonth("2026-11", 0),
    ]


def test_build_velocity_series_ignores_earlier_through():
    # A stale/rebased author date before the data must not prepend leading zeros
    series = build_velocity_series(["2026-05", "2026-06"], through="2025-01")

    assert [m.month for m in series] == ["2026-05", "2026-06"]
    assert all(m.commits == 1 for m in series)


def test_build_velocity_series_anchors_to_window_start():
    # A revived project must show its idle months, not a 3-month slice
    series = build_velocity_series(["2026-09"], through="2026-11", start="2026-01")

    assert [m.month for m in series] == [
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
        "2026-10",
        "2026-11",
    ]
    assert [m.commits for m in series] == [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]


def test_build_velocity_series_trims_months_before_window_start():
    # A commit authored days before the window opens must not add a 13th row
    series = build_velocity_series(["2025-11", "2025-12", "2026-11"], through="2026-11", start="2025-12")

    assert len(series) == 12
    assert series[0].month == "2025-12"
    assert series[-1].month == "2026-11"


def test_build_velocity_series_empty():
    assert build_velocity_series([]) == []
    assert build_velocity_series([], through="2026-11") == [VelocityMonth("2026-11", 0)]


def test_assess_velocity_trend_accelerating():
    series = [VelocityMonth(f"2026-0{i}-01", c) for i, c in enumerate([10, 10, 10, 30, 30, 30], start=1)]
    assert assess_velocity_trend(series) == "ACCELERATING"


def test_assess_velocity_trend_decelerating():
    series = [VelocityMonth(f"2026-0{i}-01", c) for i, c in enumerate([40, 40, 40, 10, 10, 10], start=1)]
    assert assess_velocity_trend(series) == "DECELERATING"


def test_assess_velocity_trend_steady_and_band_edges():
    steady = [VelocityMonth(f"2026-0{i}-01", c) for i, c in enumerate([20, 20, 20, 21, 18, 20], start=1)]
    assert assess_velocity_trend(steady) == "STEADY"

    # Outside the ±25% band in both directions
    rising = [VelocityMonth(f"2026-0{i}-01", c) for i, c in enumerate([10, 10, 10, 12, 13, 13], start=1)]
    assert assess_velocity_trend(rising) == "ACCELERATING"  # 38 vs 30
    falling = [VelocityMonth(f"2026-0{i}-01", c) for i, c in enumerate([10, 10, 10, 7, 7, 7], start=1)]
    assert assess_velocity_trend(falling) == "DECELERATING"  # 21 vs 30

    # Exactly on the ±25% band edge is treated as a trend
    exact_top = [VelocityMonth(f"2026-0{i}-01", c) for i, c in enumerate([7, 7, 6, 8, 8, 9], start=1)]
    assert assess_velocity_trend(exact_top) == "ACCELERATING"  # 25 vs 20
    exact_bottom = [VelocityMonth(f"2026-0{i}-01", c) for i, c in enumerate([7, 7, 6, 5, 5, 5], start=1)]
    assert assess_velocity_trend(exact_bottom) == "DECELERATING"  # 15 vs 20


def test_assess_velocity_trend_handles_zero_prior_window():
    revived = [VelocityMonth(f"2026-0{i}-01", c) for i, c in enumerate([0, 0, 0, 5, 5, 5], start=1)]
    assert assess_velocity_trend(revived) == "ACCELERATING"

    dead = [VelocityMonth(f"2026-0{i}-01", 0) for i in range(1, 7)]
    assert assess_velocity_trend(dead) == "STEADY"


def test_assess_velocity_trend_insufficient_history():
    assert assess_velocity_trend([VelocityMonth("2026-01", 5), VelocityMonth("2026-02", 5)]) == "INSUFFICIENT"


def test_parse_crisis_commits_by_intent():
    commits = [
        _commit("revert: drop broken routing", sha="aaa"),
        _commit("hotfix(web): patch deploy", sha="bbb"),
        _commit("fix: rollback the deploy", sha="ccc"),
        _commit("fix(newsletter): eliminate date rollback and decouple research", sha="ddd"),
        _commit("feat: rollback-safe migrations", sha="eee"),
        _commit("docs: rollback procedure", sha="fff"),
        _commit("chore: hotfix deploy script", sha="ggg"),
        _commit("Emergency patch for provider outage", sha="hhh"),
        _commit("feat: add dark mode", sha="iii"),
    ]
    events = parse_crisis_commits(commits)

    assert [(e.commit_hash, e.kind) for e in events] == [
        ("aaa", "revert"),
        ("bbb", "hotfix"),
        ("ccc", "rollback"),
        ("hhh", "emergency"),
    ]


def test_parse_crisis_commits_malformed_subject():
    assert parse_crisis_commits([_commit("", sha="a")]) == []
    assert parse_crisis_commits([_commit("   ", sha="a")]) == []
    assert [e.kind for e in parse_crisis_commits([_commit("Rollback", sha="a")])] == ["rollback"]


def test_feature_commits_are_not_crises():
    # "feat: rollback support for migrations" ships a capability, it is not firefighting
    for subject in (
        "feat: rollback support for migrations",
        "feat(api): add emergency-contact export",
        "feature: rollback-safe migration runner",
        "feat(rollback): harden undo path",
        "docs(rollback): document the procedure",
        "chore(hotfix): relocate the script",
        "test(revert): cover undo",
        "refactor: rollback handler cleanup",
        "perf: emergency fund calc fast path",
    ):
        assert parse_crisis_commits([_commit(subject)]) == []

    # The type itself still wins when it names a crisis response
    assert [e.kind for e in parse_crisis_commits([_commit("hotfix: rollback support for migrations")])] == ["hotfix"]
    assert [e.kind for e in parse_crisis_commits([_commit("hotfix(web): patch deploy")])] == ["hotfix"]
    # A scope keyword alone is not a crisis: fixing code in a rollback module is normal work
    assert parse_crisis_commits([_commit("fix(rollback): handle empty snapshot")]) == []


def test_bot_detection_covers_ci_identities():
    assert is_bot_author("github-actions", "actions@github.com")
    assert is_bot_author("actions-user", "actions-user@github.com")
    assert is_bot_author("dependabot-preview", "x@y.com")
    assert is_bot_author("renovate", "renovate@example.com")
    assert is_bot_author("google-labs-jules[bot]", "161369871+google-labs-jules[bot]@users.noreply.github.com")
    assert not is_bot_author("Cesar Vega", "g.vega.cl@gmail.com")
    assert not is_bot_author("Renata Lopez", "renata@example.com")


def test_identity_falls_back_to_display_name_without_email():
    # Documented limitation: without an email there is no way to merge identities
    commits = [
        _commit("a", author="g-vega-cl", email=""),
        _commit("b", author="Cesar Vega", email=""),
    ]
    authors = count_authors(commits)

    assert len(authors) == 2
    assert {a.identity for a in authors} == {"g-vega-cl", "cesar vega"}


def test_blank_author_and_email_never_produce_a_nameless_author():
    authors = count_authors([_commit("a", author="", email=""), _commit("b", author="", email="")])

    assert len(authors) == 1
    assert authors[0].name == "unknown"
    assert authors[0].identity == "unknown"


def test_assess_crisis_cadence_boundaries():
    one = [CrisisEvent("h", "hotfix", "hotfix")]
    assert assess_crisis_cadence([], months=12) == "STABLE"
    assert assess_crisis_cadence(one * 6, months=12) == "STABLE"  # 0.5 per month
    assert assess_crisis_cadence(one * 7, months=12) == "WATCH"
    assert assess_crisis_cadence(one * 12, months=12) == "WATCH"  # 1.0 per month
    assert assess_crisis_cadence(one * 13, months=12) == "ELEVATED"
    # A zero-month denominator must never divide by zero
    assert assess_crisis_cadence(one * 2, months=0) == "ELEVATED"


def test_parse_author_log():
    raw = f"alice{UNIT_SEPARATOR}a@x.com\n\nbob{UNIT_SEPARATOR}b@x.com\n"
    assert parse_author_log(raw) == [("alice", "a@x.com"), ("bob", "b@x.com")]


def test_inactive_contributors_respects_identity_threshold_and_bots():
    all_time = [
        ("g-vega-cl", "g.vega.cl@gmail.com"),
        ("g-vega-cl", "g.vega.cl@gmail.com"),
        ("g-vega-cl", "g.vega.cl@gmail.com"),
        ("Cesar Vega", "g.vega.cl@gmail.com"),
        ("ghost", "ghost@x.com"),
        ("ghost", "ghost@x.com"),
        ("renovate[bot]", "bot@x.com"),
        ("renovate[bot]", "bot@x.com"),
        ("renovate[bot]", "bot@x.com"),
    ]
    # Active identity wins regardless of display name; bots and one-off authors are ignored
    assert inactive_contributors(all_time, {"g.vega.cl@gmail.com"}) == []

    departed = [("departed", "departed@x.com")] * 3
    assert inactive_contributors(all_time + departed, {"g.vega.cl@gmail.com"}) == ["departed"]


def test_build_team_report_end_to_end():
    commits = [
        _commit("feat: start", month="2026-09"),
        _commit("fix: bug", month="2026-09"),
        _commit("hotfix: patch", month="2026-10"),
        _commit("feat: more", author="bob", email="bob@x.com", month="2026-11"),
    ]
    report = build_team_report(
        commits,
        all_time_authors=[("alice", "alice@example.com")] * 3,
        since="60 days ago",
        today=TODAY,
    )

    assert report.total_commits == 4
    # "60 days ago" resolves to a 2-month window, not the observed 3-month span
    assert report.window_months == 2
    assert report.window_months_source == "since"
    assert [m.month for m in report.velocity] == ["2026-09", "2026-10", "2026-11"]
    assert report.bus_factor_author == "alice"
    assert round(report.bus_factor, 3) == 0.75
    assert len(report.crisis_events) == 1
    assert report.crisis_status == "STABLE"  # 1 crisis / 2 months = 0.5, the STABLE edge
    assert report.inactive_authors == []


def test_build_team_report_empty_window():
    report = build_team_report([], all_time_authors=[], since="60 days ago", today=TODAY)

    assert report.total_commits == 0
    assert report.concentration == "UNKNOWN"
    assert report.bus_factor_author is None
    # The stated denominator matches the one used for the crisis rate
    assert report.window_months == 2
    assert report.crisis_status == "STABLE"


def test_window_months_for_relative_and_iso_windows():
    assert window_months_for("90 days ago", TODAY) == 3
    assert window_months_for("60 days ago", TODAY) == 2
    assert window_months_for("4 weeks ago", TODAY) == 1
    assert window_months_for("6 months ago", TODAY) == 6
    assert window_months_for("1 year ago", TODAY) == 12
    assert window_months_for("2026-08-01", TODAY) == 4
    assert window_months_for("last tuesday", TODAY) is None


def test_window_months_prefers_requested_window_over_observed_span():
    # All commits land in one month, but a 90-day window still spans 3 months
    commits = [_commit("hotfix: a", month="2026-11"), _commit("hotfix: b", month="2026-11")]
    report = build_team_report(commits, all_time_authors=[], since="90 days ago", today=TODAY)

    assert report.window_months == 3
    assert report.crisis_status == "WATCH"  # 2 crises / 3 months, not ELEVATED


def test_analyze_team_issues_one_scoped_log_pass():
    window_log = "\n".join([_record("feat: a"), "apps/engine/main.py", _record("fix: b", sha="def5678")])
    author_log = f"alice{UNIT_SEPARATOR}alice@example.com"
    velocity_log = "2026-10\n2026-11\n"

    def fake_git(args: list[str]) -> str:
        joined = " ".join(args)
        if "--format=%ad" in args:
            return velocity_log
        if "format=%an" in joined and "--since" not in joined:
            return author_log
        return window_log

    with patch("apps.engine.hotspot_team._run_git", side_effect=fake_git) as mock_run_git:
        report = analyze_team(since="90 days ago", scopes=["apps/", "packages/"], today=TODAY)

    assert report.total_commits == 2
    assert report.bus_factor_author == "alice"

    calls = [call.args[0] for call in mock_run_git.call_args_list]
    window_args = next(args for args in calls if "format=COMMIT" in " ".join(args))
    velocity_calls = [args for args in calls if "--format=%ad" in args]
    all_time_calls = [args for args in calls if "format=%an" in " ".join(args) and "--since" not in " ".join(args)]

    assert "--since=90 days ago" in window_args
    assert "--no-merges" in window_args
    assert window_args[-3:] == ["--", "apps/", "packages/"]
    # Every pass is scoped and bounded: no unscoped all-history scan
    assert [args[-3:] for args in velocity_calls] == [["--", "apps/", "packages/"]]
    assert [args[-3:] for args in all_time_calls] == [["--", "apps/", "packages/"]]


def test_analyze_team_from_commits_never_refetches_the_window():
    """Parity is structural: the caller's commit population is authoritative."""
    commits = to_team_commits(
        [
            type(
                "R",
                (),
                {"commit_hash": "1", "subject": "feat: a", "author": "alice", "email": "a@x.com", "month": "2026-11"},
            ),
            type(
                "R",
                (),
                {"commit_hash": "2", "subject": "hotfix: b", "author": "bob", "email": "b@x.com", "month": "2026-11"},
            ),
            type(
                "R",
                (),
                {"commit_hash": "3", "subject": "chore: c", "author": "bob", "email": "b@x.com", "month": "2026-10"},
            ),
        ]
    )

    def fake_git(args: list[str]) -> str:
        return "2026-11\n" if "--format=%ad" in args else f"bob{UNIT_SEPARATOR}b@x.com\n"

    with patch("apps.engine.hotspot_team._run_git", side_effect=fake_git) as mock_run_git:
        report = analyze_team_from_commits(commits, since="30 days ago", scopes=["apps/"], today=TODAY)

    assert report.total_commits == 3
    assert [a.name for a in report.authors] == ["bob", "alice"]
    # Velocity is anchored to the requested 12-month window, not to the data
    assert report.velocity[0].month == "2025-12"
    assert report.velocity[-1].month == "2026-11"
    assert len(report.velocity) == 12
    # Only reference passes run: velocity months and all-time authors
    assert len(mock_run_git.call_args_list) == 2
    assert all("format=COMMIT" not in " ".join(call.args[0]) for call in mock_run_git.call_args_list)


def test_unparseable_since_labels_months_as_estimated():
    commits = [_commit("hotfix: a", month="2026-11"), _commit("hotfix: b", month="2026-11")]
    report = build_team_report(commits, all_time_authors=[], since="last tuesday", today=TODAY)

    assert report.window_months_source == "observed"
    assert report.window_months == 1
    from apps.engine.hotspot_team import format_team_markdown

    assert "estimated from commits" in format_team_markdown(report)


def test_unparseable_since_without_commits_reports_assumed_months():
    from apps.engine.hotspot_team import format_team_terminal

    report = build_team_report([], all_time_authors=[], since="last tuesday", today=TODAY)

    assert report.window_months_source == "default"
    assert "1 (assumed)" in format_team_terminal(report)


def test_format_team_terminal():
    from apps.engine.hotspot_team import format_team_terminal

    report = build_team_report(
        [_commit("hotfix: patch", month="2026-11")],
        all_time_authors=[("ghost", "ghost@x.com")] * 3,
        since="12 months ago",
        today=TODAY,
    )
    output = format_team_terminal(report)

    assert "Team Health" in output
    assert "alice" in output
    assert "FRAGILE" in output
    assert "Months: 12," in output
    assert "ghost" in output
    assert "hotfix" in output


def test_format_team_terminal_unknown_bus_factor():
    from apps.engine.hotspot_team import format_team_terminal

    report = TeamReport(
        since="90 days ago",
        total_commits=0,
        authors=[],
        bus_factor=0.0,
        bus_factor_author=None,
        concentration="UNKNOWN",
        velocity=[],
        velocity_trend="INSUFFICIENT",
        crisis_events=[],
        crisis_status="STABLE",
    )
    output = format_team_terminal(report)

    assert "no human commits" in output
    assert "UNKNOWN" in output
    assert "n/a" not in output


def test_format_team_markdown():
    from apps.engine.hotspot_team import format_team_markdown

    report = build_team_report(
        [_commit("feat: x", month="2026-09"), _commit("revert: y", month="2026-11", sha="bbb2222")],
        all_time_authors=[("ghost", "ghost@x.com")] * 3,
        since="12 months ago",
        velocity_months=["2026-01", "2026-06", "2026-11"],
        today=TODAY,
    )
    md = format_team_markdown(report)

    assert "## Team Health" in md
    assert "Bus factor" in md
    assert "| 2026-11 | 1 |" in md
    assert "revert" in md
    assert "bbb2222" in md
    assert "ghost" in md
    assert "Share of window commits" in md


def test_format_team_markdown_no_crisis_no_inactive():
    from apps.engine.hotspot_team import format_team_markdown

    report = TeamReport(
        since="90 days ago",
        total_commits=5,
        authors=[AuthorMetric(name="alice", identity="a@x.com", commits=5, share=1.0, is_bot=False)],
        bus_factor=1.0,
        bus_factor_author="alice",
        concentration="FRAGILE",
        velocity=[],
        velocity_trend="INSUFFICIENT",
        crisis_events=[],
        crisis_status="STABLE",
    )
    md = format_team_markdown(report)

    assert "No revert, hotfix, emergency, or rollback commits" in md
    assert "Inactive this window" not in md
