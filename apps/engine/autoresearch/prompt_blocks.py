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
            "When CHEAP, anticipate aggressive expansion moves.\n"
            "3. Spot VIX vs Futures Drag: Query `get_volatility_index_details` for spot Cboe VIX levels (^VIX). "
            "Never mistake falling VIXY/VIXM futures ETF prices for market complacency, as futures ETFs suffer structural contango roll decay."
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
    "historical_analog_benchmarking": {
        "title": "HISTORICAL ANALOG BENCHMARKING (Precedent & Cross-Asset Reaction Check)",
        "content": (
            "=== DISCIPLINE: HISTORICAL ANALOG BENCHMARKING ===\n"
            "1. Historical Questioning: When encountering macro shifts, geopolitical escalations, rate spikes, or unusual cross-asset moves, actively ask: 'How did markets react the last time XYZ happened? What rallied, what crashed, and how did it resolve?'\n"
            '2. Precedent Pull: Invoke `research_historical_market_analog(situation="...", horizon="1m")` to retrieve verified historical episodes, empirical price reaction tapes across major benchmarks (SPY, TLT, GLD, BTC, DXY), and today\'s key structural divergences.\n'
            "3. Asymmetric Expression: Use the empirical tape and playbook to formulate long/short trade pairs and respect the falsification triggers before executing."
        ),
    },
    "market_regime_classification": {
        "title": "MARKET REGIME CLASSIFICATION (4-Quadrant Pre-Forecast Gating)",
        "content": (
            "=== FRAMEWORK: MARKET REGIME CLASSIFICATION ===\n"
            "1. Pre-Forecast State Identification: Before assigning directional conviction, classify today's pre-market environment into 1 of 4 regimes:\n"
            "- LOW_VOL_PIN: Realized vol low, spot VIX benign, heavy open interest near ATM strikes. Expect range-bound mean reversion and pin behavior; avoid chasing morning breakouts.\n"
            "- TREND_EXPANSION: Cross-asset confirmation across yields (TLT), dollar (UUP), and broad equity futures (QQQ/IWM). Trade in the direction of the confirmed macro impulse.\n"
            "- MEAN_REVERSION: Extended overnight gap (>0.4%) with diverging internal breadth or overextended 25-delta put/call skew. Anticipate opening gap-fill toward VWAP.\n"
            "- CATALYST_EVENT: Major scheduled data (CPI, NFP, FOMC) or geopolitical shock. Sizing must be conservative until initial post-open volatility settles.\n"
            "2. Regime Alignment Gate: Never assign high directional confidence (>=65%) if your thesis contradicts the dominant intraday regime."
        ),
    },
    "option_pin_gamma_levels": {
        "title": "OPTION PINNING & DEALER GAMMA LEVELS (Max Pain & Strike Walls)",
        "content": (
            "=== DISCIPLINE: OPTION PINNING & DEALER GAMMA ===\n"
            "1. Strike Wall Gravitation: Inspect options positioning, Put/Call ratios, and Max Pain strike. When spot price is within 0.3% of large open interest clusters or Max Pain, treat magnetic pin pull as the dominant intraday force.\n"
            "2. False Breakout Filter: Do not forecast aggressive intraday continuation away from major strike walls without heavy, volume-backed catalyst confirmation.\n"
            "3. Delta-Hedging Dampener: In low-volatility regimes, dealer gamma hedging compresses realized price moves; tighten target returns accordingly."
        ),
    },
    "anti_pessimism_prior_conditioning": {
        "title": "ANTI-PESSIMISM BASE-RATE PRIOR (Overcoming Macro Headline Alarmism)",
        "content": (
            "=== DISCIPLINE: ANTI-PESSIMISM BASE-RATE PRIOR ===\n"
            "1. S&P 500 Drift Base Rate: Historically, the S&P 500 closes green ~54% of all trading sessions due to structural corporate earnings growth, dividend reinvestment, and systematic equity bid.\n"
            "2. The 'Bear Porn' Filter: Do NOT default to DOWN simply because financial news highlights macroeconomic debt, geopolitical tensions, or inflation fears. Markets regularly climb a 'wall of worry' and rally on bad news already priced in.\n"
            "3. Symmetric Hurdle Discipline: Calling DOWN requires a specific, active negative catalyst (fresh hawkish shock, credit spread blowout, or violent technical rejection), not passive ambient anxiety. Likewise, calling UP requires a specific positive catalyst or constructive technical structure, not blind optimism."
        ),
    },
    "dialectical_thesis_deliberation": {
        "title": "DIALECTICAL THESIS DELIBERATION (Symmetric Bull vs Bear Balance Sheet)",
        "content": (
            "=== DISCIPLINE: DIALECTICAL THESIS DELIBERATION ===\n"
            "1. Two-Column Conviction Scoring: In your internal analysis, score both sides objectively on a 1-to-10 scale:\n"
            "   - Bull Conviction Score [1-10]: Based on confirmed earnings beats, easing yields, soft dollar, or technical hold.\n"
            "   - Bear Conviction Score [1-10]: Based on active hawkish catalysts, surging yields, strong dollar, or technical breakdown.\n"
            "2. Symmetry Invariant: Do NOT hold one direction to an impossible standard while waving the other through on passive assumptions. Both UP and DOWN require identical evidentiary hurdles.\n"
            "3. Tie-Breaking & Low-Conviction Pinning: If |Bull Score - Bear Score| <= 1, classify today as CONSOLIDATION / RANGE-BOUND. Default to moderate/low confidence (52%-54%) and require cross-asset divergence (TLT yields or Dollar DXY) to justify any directional bias."
        ),
    },
    "regime_gated_confidence_calibration": {
        "title": "REGIME-GATED CONFIDENCE CALIBRATION (Structural Clamping)",
        "content": (
            "=== DISCIPLINE: REGIME-GATED CONFIDENCE CALIBRATION ===\n"
            "1. Low-Volatility & Pinning Clamping: When market indicators show compressed volatility, flat overnight gaps (<0.2%), or proximity (<0.25%) to Max Pain strike, clamp confidence strictly between 52.0% and 55.0%. Never exceed 56% in range-bound regimes.\n"
            "2. Moderate Confirmation Range (56.0% - 65.0%): Reserve for single-catalyst clarity or one-sided sector breadth (e.g., QQQ/IWM aligned).\n"
            "3. Multi-Asset Convergence Ceiling (66.0% - 75.0%): Require independent convergence across macro news, bond yield momentum (TLT/IEF), dollar direction (UUP), and technical levels. Never exceed 80.0% confidence on any intraday prediction."
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
