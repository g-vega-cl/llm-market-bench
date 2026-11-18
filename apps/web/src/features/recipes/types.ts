export type JSONPrimitive = string | number | boolean | null;
export type JSONValue = JSONPrimitive | JSONObject | JSONArray;
export type JSONObject = { [key: string]: JSONValue };
export type JSONArray = JSONValue[];

export type RecipeCadence = '5m' | '3h' | '1d';

export interface PromptBlock {
    id: string;
    type: 'prompt';
    text: string;
}

export interface NewsBlock {
    id: string;
    type: 'news';
    contains: string[];
    recency_hours: number;
}

export interface MemoriesBlock {
    id: string;
    type: 'memories';
    contains: string[];
    recency_hours: number;
    category: string;
    min_importance: number;
}

export interface TechnicalsRule {
    id: string;
    metric: string;
    operator: '>' | '<' | '>=' | '<=' | '==';
    target: string;
}

export interface TechnicalsBlock {
    id: string;
    type: 'technicals';
    rules: TechnicalsRule[];
}

export interface OutputFormatBlock {
    id: string;
    type: 'output_format';
}

export type StrategyBlock =
    | PromptBlock
    | NewsBlock
    | MemoriesBlock
    | TechnicalsBlock
    | OutputFormatBlock;

export interface StrategyStage {
    id: string;
    blocks: StrategyBlock[];
    selected_tools: string[];
}

export interface PushStrategy {
    version: '2.0-push';
    id?: string;
    name: string;
    description?: string;
    cadence: RecipeCadence;
    /** Exactly one stage: a strategy is one LLM call. */
    stages: [StrategyStage];
}

export interface CuratedToolOption {
    name: string;
    label: string;
    description: string;
    liveOnly?: boolean;
}

export const CURATED_TOOLS: CuratedToolOption[] = [
    {
        name: 'get_technical_indicators',
        label: 'Technical Indicators',
        description: 'RSI-14, MACD, 20D VWAP, SMA-20/50, RVOL, 52W %',
    },
    {
        name: 'get_key_metrics',
        label: 'Key Metrics (P/E, FCF)',
        description: 'P/E ratio, Free Cash Flow, ROE, margins, market cap',
    },
    {
        name: 'get_price_history',
        label: 'Price History',
        description: 'Recent daily prices and volume context',
    },
    {
        name: 'get_stock_quote',
        label: 'Stock Quote',
        description: 'Current spot price and daily quote',
    },
    {
        name: 'run_stock_screener',
        label: 'Stock Screener',
        description: 'Filter universe by market cap, beta, sector, volume',
        liveOnly: true,
    },
    {
        name: 'get_todays_news_menu',
        label: 'Newsletters Menu',
        description: 'Latest Substack/financial newsletter headlines',
    },
    {
        name: 'fetch_newsletter_content',
        label: 'Fetch Newsletter',
        description: 'Read full newsletter text by source ID',
    },
    {
        name: 'search_past_memories',
        label: 'Search Memories',
        description: 'Semantic RAG search over historical market memories',
    },
    {
        name: 'get_ticker_news',
        label: 'Ticker News',
        description: 'Recent headlines for a specific stock symbol',
    },
    {
        name: 'get_market_feeling',
        label: 'Market Feeling',
        description: 'Overall market sentiment & barometer snapshot',
    },
    {
        name: 'get_earnings_history',
        label: 'Earnings History',
        description: 'Historical EPS beats, misses, and surprises',
    },
];

export interface StrategyRecipeRecord {
    id: string;
    user_id: string;
    name: string;
    description: string;
    is_public: boolean;
    is_template: boolean;
    is_live: boolean;
    cadence: RecipeCadence;
    graph_json: PushStrategy;
    trial_count: number;
    created_at: string;
    updated_at: string;
}

export interface RecipeAlert {
    id: string;
    user_id: string;
    recipe_id: string | null;
    recipe_name: string;
    ticker: string;
    action: 'BUY' | 'SELL' | 'HOLD' | 'EXIT';
    entry_price: number;
    target_price: number | null;
    stop_loss: number | null;
    timeframe: string;
    reason: string;
    context?: JSONObject;
    is_read: boolean;
    created_at: string;
}

export interface CompletedTradeRecord {
    ticker: string;
    entry_time: string;
    entry_price: number;
    exit_time: string;
    exit_price: number;
    action: string;
    shares?: number;
    pnl_midpoint: number;
    pnl_net: number;
    return_pct_midpoint: number;
    return_pct_net: number;
    exit_reason: string;
    catalyst_headline?: string;
    confidence: number;
}

export interface SkippedTradeRecord {
    time: string;
    reason: string;
    skip_type: string;
    headline?: string;
}

export interface LLMTraceToolCall {
    name: string;
    args: Record<string, unknown>;
    result: string;
}

export interface LLMTraceRound {
    round: number;
    reasoning: string;
    assistant_text: string;
    tool_calls: LLMTraceToolCall[];
}

export interface LLMExecutionTrace {
    rounds: LLMTraceRound[];
    forced_final_synthesis?: boolean;
}

export interface OpenPositionRecord {
    ticker: string;
    side?: string;
    shares: number;
    entry_price: number;
    entry_time: string;
    cost_basis?: number;
    current_price?: number;
    market_value?: number;
    unrealized_pnl_net?: number;
    unrealized_return_pct?: number;
}

export interface BacktestDayStep {
    day: string;
    day_index: number;
    status: string;
    signals: { action: string; ticker: string }[];
    tool_calls: string[];
    output_excerpt: string;
    full_output?: string;
    prompt?: string;
    trace?: LLMExecutionTrace | null;
    day_pnl_net: number;
    trades_executed: number;
    trades_skipped: number;
    open_positions_count?: number;
}

export interface BacktestResultData {
    mode?: 'backtest';
    window_dates?: string[];
    days_completed?: number;
    total_days?: number;
    current_day?: string | null;
    starting_capital?: number;
    ending_capital_midpoint?: number;
    ending_capital_net?: number;
    cash?: number;
    total_equity?: number;
    open_positions?: OpenPositionRecord[];
    total_return_pct_midpoint: number;
    total_return_pct_net: number;
    total_trades: number;
    winning_trades?: number;
    losing_trades?: number;
    win_rate_pct: number;
    profit_factor?: number;
    max_drawdown_pct: number;
    llm_calls_made?: number;
    equity_curve: { time: string; equity: number }[];
    trades: CompletedTradeRecord[];
    skipped_trades?: SkippedTradeRecord[];
    day_steps?: BacktestDayStep[];
}

export type RecipeJobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface RecipeJobRecord {
    id: string;
    recipe_id?: string;
    mode?: 'backtest' | 'live_turn';
    status: RecipeJobStatus;
    progress_pct: number;
    provider?: string;
    model?: string;
    result_json: BacktestResultData | LiveRunResult | null;
    error_message: string | null;
    created_at?: string;
    started_at?: string | null;
    completed_at?: string | null;
}

export interface RecipeRunDetail {
    job: RecipeJobRecord;
    recipeName: string | null;
    recipeCadence: RecipeCadence | null;
    queuePosition?: number | null;
    globalActiveBacktests?: number;
}

export interface RecipeUserQuotaStatus {
    tier: string;
    activeBacktests: number;
    maxConcurrentBacktests: number;
    backtestsLast24h: number;
    dailyBacktestLimit: number;
    liveTurnsLast24h: number;
    dailyLiveTurnLimit: number;
    activeLiveRecipes: number;
    maxLiveRecipes: number;
    globalPendingBacktests: number;
    globalQueueCap: number;
}

export interface RecipeSummaryItem {
    id: string;
    name: string;
    cadence: RecipeCadence;
    is_live: boolean;
    trial_count: number;
    updated_at: string;
}

export interface LiveStageOutput {
    stage_id: string;
    prompt: string;
    output: string;
    tool_calls: string[];
    trace?: LLMExecutionTrace | null;
}

export interface LiveRunResult {
    mode: 'live_turn';
    as_of_utc: string;
    slot_label?: string;
    stages: LiveStageOutput[];
    final_output: string;
    signals: { action: string; ticker: string }[];
    executed_signals?: { action: string; ticker: string; price?: number }[];
    signal_prices?: Record<string, number>;
    updated_portfolio?: {
        paper_cash: number;
        paper_positions: OpenPositionRecord[];
        paper_trades: CompletedTradeRecord[];
        paper_equity_curve: { time: string; equity: number }[];
    };
}

export interface LivePortfolioSnapshot {
    cash: number;
    total_equity: number;
    open_positions: OpenPositionRecord[];
    trades: CompletedTradeRecord[];
}

export interface LivePortfolioAndRuns {
    portfolio: LivePortfolioSnapshot;
    recentLiveRuns: RecipeJobRecord[];
}

/**
 * Backtest error state surfaced in StudioAlertSlot.
 *
 * Replaces the old ExecutionState union. The studio page no longer
 * executes live turns (only the daemon does), so the only async
 * execution path left is Backtest, which navigates away on success.
 * A failure here is always an error — there is no "running" or
 * "done" state to track.
 */
export interface BacktestError {
    kind: 'quota' | 'navigation' | 'execution';
    message: string;
    /** Only set for navigation failures — lets the alert offer "Open Backtest Run →". */
    backtestJobId?: string;
}

export type PreviewState =
    | { status: 'template' }
    | { status: 'loading' }
    | { status: 'hydrated'; hydratedByBlockId: Record<string, string> }
    | { status: 'error'; message: string };
