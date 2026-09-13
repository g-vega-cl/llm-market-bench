"""Modular Prompt Blocks Registry for Auto-Researcher.

Provides reusable, structured trading discipline and reasoning blocks that the
Auto-Researcher can dynamically enable or disable via `selected_prompt_blocks`.
"""

AVAILABLE_PROMPT_BLOCKS: dict[str, dict[str, str]] = {
    "let_winners_run": {
        "title": "LET WINNERS RUN (Momentum & Trailing Take-Profit)",
        "content": (
            "=== DISCIPLINE: LET WINNERS RUN ===\n"
            "1. Trailing Profit Ratchet: When a position shows positive unrealized gains and its underlying catalyst remains intact, "
            "do NOT liquidate early to lock in modest profits. Allow winners to run.\n"
            "2. Momentum Scale-In: If news catalysts or market flows reinforce a winning ticker, consider scaling into the position "
            "rather than capping portfolio exposure.\n"
            "3. Thesis Realization Gate: Only execute a SELL on a profitable asset when the primary thesis has fully materialized or "
            "a superior, higher-conviction catalyst requires capital reallocation."
        ),
    },
    "cut_losers_fast": {
        "title": "CUT LOSERS FAST (Asymmetric Risk & Thesis Invalidation)",
        "content": (
            "=== DISCIPLINE: CUT LOSERS FAST ===\n"
            "1. Rapid Thesis Invalidation: If news, macro shifts, or earnings metrics contradict your original purchase rationale, "
            "immediately exit the position. Do NOT hold on hope or wait for breakeven.\n"
            "2. Asymmetric Stop-Loss Guardrail: Treat any position exhibiting persistent negative momentum or >5% drawdowns with extreme skepticism. "
            "Prioritize capital preservation over loss-aversion bias.\n"
            "3. No Sunk-Cost Averaging: Never buy more shares of a declining asset simply to lower cost basis unless a clear, new catalyst has emerged."
        ),
    },
    "catalyst_expiry_timer": {
        "title": "CATALYST EXPIRY TIMER (Time-Based Exit Discipline)",
        "content": (
            "=== DISCIPLINE: CATALYST EXPIRY TIMER ===\n"
            "1. Strict Timeline Alignment: Match position duration to the expected news cycle. If a SHORT_TERM catalyst passes without positive price movement within 48 hours, exit.\n"
            "2. Dead Capital Avoidance: Liquidate stagnant positions where catalyst momentum has dissipated to free up buying power for fresh opportunities."
        ),
    },
    "five_whys_causal": {
        "title": "5 WHYS CAUSAL DEPTH (Root-Cause Validation)",
        "content": (
            "=== FRAMEWORK: 5 WHYS CAUSAL DEPTH ===\n"
            "1. Drill down to root causes of market events by repeatedly asking 'Why?'.\n"
            "2. Avoid reacting to superficial headline noise. Trace the underlying supply/demand driver before placing trades."
        ),
    },
    "mece_risk_partition": {
        "title": "MECE RISK PARTITIONING (Exhaustive Scenario Analysis)",
        "content": (
            "=== FRAMEWORK: MECE RISK PARTITIONING ===\n"
            "1. Partition analysis, risk factors, and macro scenarios into Mutually Exclusive, Collectively Exhaustive buckets.\n"
            "2. Ensure zero blindspots across upside catalysts, downside risks, and industry correlation."
        ),
    },
    "options_vol_discipline": {
        "title": "OPTIONS VOLATILITY DISCIPLINE (Cone & Implied Move Bounds)",
        "content": (
            "=== DISCIPLINE: OPTIONS VOLATILITY CONE ===\n"
            "1. Implied Move Bounding: Invoke `get_options_vol_surface` to inspect the 1-sigma options-implied daily move cone. "
            "Do NOT project intraday price targets exceeding this cone without extreme multi-signal catalyst confirmation.\n"
            "2. IV Premium Regime Awareness: When IV Premium is RICH (IV > RV20), respect mean-reversion pullbacks and avoid buying extended breakout tops. "
            "When CHEAP, anticipate aggressive expansion moves."
        ),
    },
    "macro_regime_routing": {
        "title": "MACRO REGIME ROUTING (Yield Curve & Monetary Flow Alignment)",
        "content": (
            "=== FRAMEWORK: MACRO REGIME ROUTING ===\n"
            "1. Curve Regime Alignment: Invoke `get_yield_curve_regime` on economic data or Fed days. "
            "Align asset allocations with historical factor tailwinds:\n"
            "- BULL_STEEPENER: Favor Small-Caps (IWM), Regional Banks (KRE), and high-beta cyclicals.\n"
            "- BULL_FLATTENER: Favor Mega-Cap Growth (QQQ) and duration.\n"
            "- BEAR_STEEPENER: Favor Energy (XLE), Commodities, and Value.\n"
            "- BEAR_FLATTENER: Favor Defensives (XLP/XLV) or Cash preservation."
        ),
    },
    "disconfirming_evidence_gate": {
        "title": "DISCONFIRMING EVIDENCE GATE (Falsifiable Thesis Discipline)",
        "content": (
            "=== DISCIPLINE: DISCONFIRMING EVIDENCE GATE ===\n"
            "1. Falsification Before Sizing: Before increasing exposure to an asset, query `track_thesis_pillars` and identify at least ONE disconfirming signal that could prove your trade wrong.\n"
            "2. Automatic Conviction Downgrade: If disconfirming evidence emerges against a core pillar, immediately downgrade conviction to WEAKENED and tighten stop-loss thresholds."
        ),
    },
    "catalyst_radar_discipline": {
        "title": "CATALYST RADAR (Upcoming & Digesting Events)",
        "content": (
            "=== DISCIPLINE: CATALYST RADAR ===\n"
            "1. Pre-Trade Radar Scan: Invoke `get_catalyst_radar` to inspect high-velocity concepts with upcoming or actively digesting calendar triggers before initiating large directional trades.\n"
            "2. Asymmetric Event Timing: If a high-impact catalyst is scheduled within 7 days (or currently in 1-3 day market digestion), account for event volatility and potential reversal risk rather than assuming linear trend continuation."
        ),
    },
    "forward_calendar_scenario_anticipation": {
        "title": "FORWARD CALENDAR & SCENARIO ANTICIPATION (Tomorrow & Next Week Positioning)",
        "content": (
            "=== DISCIPLINE: FORWARD CALENDAR & SCENARIO ANTICIPATION ===\n"
            "1. Forward Catalyst Questioning: Before placing trades, actively think:\n"
            "   - 'What is scheduled to happen tomorrow? What will happen next week?'\n"
            "   - 'How can I position now to profit from these scheduled events before the market moves?'\n"
            '2. Tool-Driven Scenario Pull: Invoke `get_calendar_scenario_analysis(timeframe="tomorrow")` or `timeframe="next_week"` to pull scheduled macro/corporate triggers, scenario probability trees (Bull/Base/Bear), conditional trading plans, and discovered investable assets.\n'
            "3. Historical Playbook Check: Evaluate historical precedent memories returned by the tool to understand how similar past catalysts actually impacted asset prices."
        ),
    },
    "ticker_news_verification": {
        "title": "TICKER NEWS VERIFICATION (Single-Stock Catalyst Check)",
        "content": (
            "=== DISCIPLINE: TICKER NEWS VERIFICATION ===\n"
            "1. On-Demand News Pull: When evaluating a specific stock ticker cited in newsletter summaries or screener results, invoke `get_ticker_news(ticker=TICKER, limit=5)` to verify whether recent breaking headlines or earnings releases confirm or invalidate the trade setup.\n"
            "2. Noise Filter: Distinguish between promotional commentary and concrete material catalysts (earnings surprises, M&A, regulatory rulings, contract awards) before committing capital."
        ),
    },
}


def render_prompt_blocks(block_ids: list[str] | None) -> str:
    """Renders selected modular prompt blocks into formatted system prompt text.

    Args:
        block_ids: List of block keys selected by the Auto-Researcher.

    Returns:
        Formatted markdown string containing all valid selected blocks.
    """
    if not block_ids:
        return ""

    rendered_sections = []
    for block_id in block_ids:
        if block_id in AVAILABLE_PROMPT_BLOCKS:
            block = AVAILABLE_PROMPT_BLOCKS[block_id]
            rendered_sections.append(f"### {block['title']}\n{block['content']}")

    if not rendered_sections:
        return ""

    return "\n\n=== MODULAR TRADING DISCIPLINE & REASONING BLOCKS ===\n" + "\n\n".join(rendered_sections) + "\n\n"
