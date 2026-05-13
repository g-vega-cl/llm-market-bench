"""Auto-Research prompt improver package.

Karpathy-style autonomous prompt improvement: evaluates 1 week of live
trading performance, proposes prompt changes, activates the best variant.
"""

from .evaluator import evaluate_week
from .metrics import (
    compute_score,
    compute_wall_street_metrics,
)
from .prompt_store import (
    clear_active_prompt_cache,
    get_active_prompt,
    get_baseline_metrics,
    get_previous_variants,
    revert_to_baseline,
    revert_to_previous,
    save_variant,
)
from .researcher import PromptResearchResult, run_research
from .runner import run
from .window import get_week_window

__all__ = [
    "compute_wall_street_metrics",
    "compute_score",
    "evaluate_week",
    "run_research",
    "PromptResearchResult",
    "get_active_prompt",
    "save_variant",
    "get_previous_variants",
    "get_baseline_metrics",
    "revert_to_previous",
    "revert_to_baseline",
    "clear_active_prompt_cache",
    "run",
    "get_week_window",
]
