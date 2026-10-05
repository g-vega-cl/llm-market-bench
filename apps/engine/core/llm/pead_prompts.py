"""Prompt definitions and Jev criteria contracts for Post-Earnings Announcement Drift (PEAD)."""

import json

PEAD_JEV_QUESTION_KEY = "pead_admission"
PEAD_JEV_QUESTION_TYPE = "choice"
PEAD_JEV_INSTRUCTIONS = (
    "Determine whether this stock qualifies for admission into the Post-Earnings Announcement Drift "
    "(PEAD) systematic portfolio based on reported EPS surprise, revenue surprise, earnings quality, "
    "forward guidance, and absence of extreme pre-earnings run-up."
)

PEAD_DEFAULT_CRITERIA = {
    "QUALIFIED": (
        "Strong earnings print with top-decile SUE (Standardized Unexpected Earnings >= 2.0), "
        "positive revenue growth surprise, clean Sloan cash accruals (operating cash flow confirms "
        "reported earnings), forward guidance stable or raised, and no parabolic run-up (>25% in 20 days)."
    ),
    "DISQUALIFIED": (
        "Low quality or trap print: EPS beat driven by one-off non-operating items or working capital accruals, "
        "revenue miss, lowered forward guidance, margin contraction, or extreme pre-announcement run-up "
        "leading to sell-the-news exhaustion."
    ),
}


def format_pead_jev_criteria(criteria: dict[str, str]) -> str:
    """Format PEAD Jev criteria dictionary into JSON string."""
    clean_criteria = {
        "QUALIFIED": criteria.get("QUALIFIED", PEAD_DEFAULT_CRITERIA["QUALIFIED"]).strip(),
        "DISQUALIFIED": criteria.get("DISQUALIFIED", PEAD_DEFAULT_CRITERIA["DISQUALIFIED"]).strip(),
    }
    return json.dumps(clean_criteria, indent=2)


def parse_pead_jev_criteria(prompt_content: str | None) -> dict[str, str]:
    """Parse PEAD Jev criteria dictionary from JSON string with fallback to defaults."""
    if not prompt_content:
        return dict(PEAD_DEFAULT_CRITERIA)
    try:
        data = json.loads(prompt_content)
        if isinstance(data, dict) and "QUALIFIED" in data and "DISQUALIFIED" in data:
            return {
                "QUALIFIED": str(data["QUALIFIED"]).strip(),
                "DISQUALIFIED": str(data["DISQUALIFIED"]).strip(),
            }
    except Exception:
        pass
    return dict(PEAD_DEFAULT_CRITERIA)
