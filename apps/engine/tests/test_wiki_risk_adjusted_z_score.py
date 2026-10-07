"""Tests ensuring comprehensive documentation of the Unified Risk-Adjusted Z-Score across wiki pages.

Verifies formula accuracy, cross-page linking, rationale ('why we added it'),
and disambiguation between Portfolio Autoresearch and other research loops.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WIKI_DIR = REPO_ROOT / "wiki"


def test_risk_adjusted_z_score_concept_page():
    path = WIKI_DIR / "concepts" / "risk-adjusted-z-score.md"
    assert path.exists(), "wiki/concepts/risk-adjusted-z-score.md must exist"
    content = path.read_text()

    # Mathematical elements
    assert "Composite Excess Return" in content
    assert "Weekly Effective Volatility" in content
    assert "DRAWDOWN_PENALTY_WEIGHT = 0.3" in content
    assert "VOLATILITY_ANNUAL_FLOOR = 10.0" in content

    # The "Why we added it" rationale
    assert "Why We Added It" in content or "Rationale" in content
    assert "Karpathy Ratchet Lockout" in content or "ratchet lockout" in content.lower()
    assert "July 19" in content
    assert "2.52" in content
    assert "regime" in content.lower()
    assert "meme" in content.lower() or "idiosyncratic" in content.lower()
    assert "backfill_normalized_scores.py" in content


def test_autoresearch_entity_page():
    path = WIKI_DIR / "entities" / "autoresearch.md"
    assert path.exists(), "wiki/entities/autoresearch.md must exist"
    content = path.read_text()

    # Disambiguation and formula
    assert "[[concepts/risk-adjusted-z-score]]" in content
    assert "Unified Risk-Adjusted Z-Score" in content
    assert "Weekly Effective Volatility" in content
    # Rationale and historical context
    assert "July 19" in content or "outlier" in content.lower()
    assert "apps/engine/autoresearch/" in content


def test_autoresearch_arena_entity_page():
    path = WIKI_DIR / "entities" / "autoresearch-arena.md"
    assert path.exists(), "wiki/entities/autoresearch-arena.md must exist"
    content = path.read_text()

    # Portfolio score audit section & link
    assert "[[concepts/risk-adjusted-z-score]]" in content
    assert "Weekly Effective Volatility" in content or "Z-Score" in content
    assert "ScoreCalculation.tsx" in content
    assert "ScoreBreakdown.tsx" in content


def test_auditability_concept_page():
    path = WIKI_DIR / "concepts" / "auditability.md"
    assert path.exists(), "wiki/concepts/auditability.md must exist"
    content = path.read_text()

    assert "[[concepts/risk-adjusted-z-score]]" in content
    assert "Unified Risk-Adjusted Z-Score" in content or "Z-score" in content


def test_transparency_standard_concept_page():
    path = WIKI_DIR / "concepts" / "transparency-standard.md"
    assert path.exists(), "wiki/concepts/transparency-standard.md must exist"
    content = path.read_text()

    assert "[[concepts/risk-adjusted-z-score]]" in content


def test_multi_track_autoresearch_concept_page():
    path = WIKI_DIR / "concepts" / "multi-track-autoresearch.md"
    assert path.exists(), "wiki/concepts/multi-track-autoresearch.md must exist"
    content = path.read_text()

    assert "[[concepts/risk-adjusted-z-score]]" in content


def test_prompt_experiment_lifecycle_concept_page():
    path = WIKI_DIR / "concepts" / "prompt-experiment-lifecycle.md"
    assert path.exists(), "wiki/concepts/prompt-experiment-lifecycle.md must exist"
    content = path.read_text()

    assert "[[concepts/risk-adjusted-z-score]]" in content


def test_web_app_entity_page():
    path = WIKI_DIR / "entities" / "web-app.md"
    assert path.exists(), "wiki/entities/web-app.md must exist"
    content = path.read_text()

    assert "[[concepts/risk-adjusted-z-score]]" in content
