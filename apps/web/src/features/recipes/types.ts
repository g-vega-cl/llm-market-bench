export type JSONPrimitive = string | number | boolean | null;
export type JSONValue = JSONPrimitive | JSONObject | JSONArray;
export type JSONObject = { [key: string]: JSONValue };
export type JSONArray = JSONValue[];

export type RecipeCadence = '5m' | '1d';

export type NodeType =
    | 'news_source'
    | 'price_tape'
    | 'technical_gate'
    | 'classification'
    | 'generative_analyst'
    | 'risk_output';

export interface ConditionRule {
    metric: string;
    operator: '>' | '<' | '>=' | '<=' | '==';
    target: number | string;
}

export interface DAGNode {
    id: string;
    type: NodeType;
    title: string;
    config: JSONObject;
}

export interface DAGEdge {
    from: string;
    to: string;
}

export interface RecipeGraph {
    version?: string;
    id?: string;
    name: string;
    description?: string;
    cadence: RecipeCadence;
    concurrency?: {
        max_open_trades?: number;
        max_equity_pct_per_trade?: number;
    };
    nodes: DAGNode[];
    edges: DAGEdge[];
}

export interface StrategyRecipeRecord {
    id: string;
    user_id: string;
    name: string;
    description: string;
    is_public: boolean;
    is_template: boolean;
    is_live: boolean;
    cadence: RecipeCadence;
    graph_json: RecipeGraph;
    concurrency_config: {
        max_open_trades: number;
        max_equity_pct_per_trade: number;
    };
    paper_cash: number;
    paper_positions: JSONArray;
    paper_trades: JSONArray;
    paper_equity_curve: JSONArray;
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
    shares: number;
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

export interface WeekBreakdown {
    week: string;
    trades_count?: number;
    trades?: number;
    week_pnl_midpoint?: number;
    pnl_midpoint?: number;
    week_pnl_net?: number;
    pnl_net?: number;
    ending_equity?: number;
}

export interface BacktestResultData {
    starting_capital: number;
    ending_capital_midpoint: number;
    ending_capital_net: number;
    total_return_pct_midpoint: number;
    total_return_pct_net: number;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate_pct: number;
    profit_factor: number;
    max_drawdown_pct: number;
    llm_calls_made: number;
    equity_curve: Array<{ time: string; equity_midpoint: number; equity_net: number }>;
    trades: CompletedTradeRecord[];
    skipped_trades: SkippedTradeRecord[];
    weeks_breakdown: WeekBreakdown[];
}
