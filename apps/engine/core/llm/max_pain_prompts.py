"""Prompt definitions and Jev criteria contracts for Daily Options Max Pain Strategy."""

import json

MAX_PAIN_JEV_QUESTION_KEY = "max_pain_admission"
MAX_PAIN_JEV_QUESTION_TYPE = "choice"
MAX_PAIN_JEV_INSTRUCTIONS = (
    "Determine whether this index ETF qualifies for admission into the Daily Options Max Pain "
    "systematic portfolio based on 0DTE dealer gamma concentration, discount distance to Max Pain "
    "strike, and absence of extreme market-wide catalyst or unpinning breakout risk."
)

MAX_PAIN_DEFAULT_CRITERIA = {
    "QUALIFIED": (
        "Concentrated 0DTE options open interest establishing clear market maker gamma pinning "
        "gravity toward the Max Pain strike. Spot price trading at a healthy convergence discount "
        "(0.25% to 2.50% below strike), balanced Put/Call ratio, and absence of imminent binary "
        "macro shock (FOMC rate decision, emergency geopolitics) that would overpower dealer hedging."
    ),
    "DISQUALIFIED": (
        "High risk of gamma unpinning or runaway trend: major binary macro catalyst underway, "
        "extreme directional volume breaking dealer gamma support, spot already at or above "
        "Max Pain strike, or negligible 0DTE open interest depth unable to constrain price movement."
    ),
}


def format_max_pain_jev_criteria(criteria: dict[str, str]) -> str:
    """Format Max Pain Jev criteria dictionary into JSON string."""
    clean_criteria = {
        "QUALIFIED": criteria.get("QUALIFIED", MAX_PAIN_DEFAULT_CRITERIA["QUALIFIED"]).strip(),
        "DISQUALIFIED": criteria.get("DISQUALIFIED", MAX_PAIN_DEFAULT_CRITERIA["DISQUALIFIED"]).strip(),
    }
    return json.dumps(clean_criteria, indent=2)


def parse_max_pain_jev_criteria(prompt_content: str | None) -> dict[str, str]:
    """Parse Max Pain Jev criteria dictionary from JSON string with fallback to defaults."""
    if not prompt_content:
        return dict(MAX_PAIN_DEFAULT_CRITERIA)
    try:
        data = json.loads(prompt_content)
        if isinstance(data, dict) and "QUALIFIED" in data and "DISQUALIFIED" in data:
            return {
                "QUALIFIED": str(data["QUALIFIED"]).strip(),
                "DISQUALIFIED": str(data["DISQUALIFIED"]).strip(),
            }
    except Exception:
        pass
    return dict(MAX_PAIN_DEFAULT_CRITERIA)
