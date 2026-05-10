"""Auto-Research prompt improver package.

Karpathy-style autonomous prompt improvement: evaluates 1 week of live
trading performance, proposes prompt changes, activates the best variant.
"""

from .metrics import (
    compute_wall_street_metrics,
    compute_composite_score,
)
from .decision_quality import compute_decision_quality
from .evaluator import evaluate_week
from .researcher import run_research, PromptResearchResult
from .prompt_store import (
    get_active_prompt,
    save_variant,
    get_previous_variants,
    get_baseline_metrics,
    revert_to_previous,
    clear_active_prompt_cache,
)
from .runner import run
from .validator import validate_prompt
from .window import get_week_window

__all__ = [
    "compute_wall_street_metrics",
    "compute_composite_score",
    "compute_decision_quality",
    "evaluate_week",
    "run_research",
    "PromptResearchResult",
    "get_active_prompt",
    "save_variant",
    "get_previous_variants",
    "get_baseline_metrics",
    "revert_to_previous",
    "clear_active_prompt_cache",
    "run",
    "validate_prompt",
    "get_week_window",
]
