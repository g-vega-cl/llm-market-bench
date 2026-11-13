export type JSONPrimitive = string | number | boolean | null;
export type JSONValue = JSONPrimitive | JSONObject | JSONArray;
export type JSONObject = { [key: string]: JSONValue };
export type JSONArray = JSONValue[];

export type RecipeCadence = '5m' | '1d';

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
    title: string;
    blocks: StrategyBlock[];
    selected_tools: string[];
}

export interface PushStrategy {
    version: '2.0-push';
    id?: string;
    name: string;
    description?: string;
    cadence: RecipeCadence;
    stages: StrategyStage[];
}

export interface CuratedToolOption {
    name: string;
    label: string;
    description: string;
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
    {
        name: 'web_search',
        label: 'Web Search',
        description: 'Live web search for breaking macro/company news',
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

export interface BacktestResultData {
    window_dates?: string[];
    starting_capital?: number;
    ending_capital_midpoint?: number;
    ending_capital_net?: number;
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
}

export interface LiveStageOutput {
    stage_id: string;
    title: string;
    prompt: string;
    output: string;
    tool_calls: string[];
}

export interface LiveRunResult {
    mode: 'live_turn';
    as_of_utc: string;
    stages: LiveStageOutput[];
    final_output: string;
    signals: { action: string; ticker: string }[];
}

export type ExecutionState =
    | { status: 'idle' }
    | { status: 'running'; mode: 'live_turn' | 'backtest' }
    | { status: 'live_done'; result: LiveRunResult }
    | { status: 'backtest_done'; result: BacktestResultData }
    | { status: 'error'; message: string };

export type PreviewState =
    | { status: 'template' }
    | { status: 'loading' }
    | { status: 'hydrated'; hydratedByBlockId: Record<string, string> }
    | { status: 'error'; message: string };
