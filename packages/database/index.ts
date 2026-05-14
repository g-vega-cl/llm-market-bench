export type { Database } from './supabase-types';

export type Memory = {
    id: string;
    content: string;
    created_at: string | null;
    metadata: Record<string, any>;
    status: string | null;
    parent_id: string | null;
    relationship_type: string | null;
    relevance_score: number | null;
    memory_type: string | null;
    importance_score: number | null;
    target_date: string | null;
};

export type MemoryInsert = {
    id?: string;
    content: string;
    created_at?: string | null;
    metadata?: Record<string, any>;
    status?: string | null;
    parent_id?: string | null;
    relationship_type?: string | null;
    relevance_score?: number | null;
    memory_type?: string | null;
    importance_score?: number | null;
    target_date?: string | null;
};

export type MemoryUpdate = {
    id?: string;
    content?: string;
    created_at?: string | null;
    metadata?: Record<string, any>;
    status?: string | null;
    parent_id?: string | null;
    relationship_type?: string | null;
    relevance_score?: number | null;
    memory_type?: string | null;
    importance_score?: number | null;
    target_date?: string | null;
};

export type Decision = {
    id: string;
    source_id: string;
    ticker: string;
    signal: string;
    confidence: number;
    reasoning: string;
    model_provider: string;
    model_name: string;
    created_at: string | null;
    status: string | null;
    price: number | null;
    trade_id: string | null;
    metadata: Record<string, any>;
    limit_price: number | null;
};

export type DecisionInsert = {
    id?: string;
    source_id: string;
    ticker: string;
    signal: string;
    confidence: number;
    reasoning: string;
    model_provider: string;
    model_name: string;
    created_at?: string | null;
    status?: string | null;
    price?: number | null;
    trade_id?: string | null;
    metadata?: Record<string, any>;
    limit_price?: number | null;
};

export type DecisionUpdate = {
    id?: string;
    source_id?: string;
    ticker?: string;
    signal?: string;
    confidence?: number;
    reasoning?: string;
    model_provider?: string;
    model_name?: string;
    created_at?: string | null;
    status?: string | null;
    price?: number | null;
    trade_id?: string | null;
    metadata?: Record<string, any>;
    limit_price?: number | null;
};

export type Trade = {
    id: string;
    portfolio_id: string;
    ticker: string;
    signal: string;
    quantity: number;
    price: number;
    total_cost: number;
    executed_at: string | null;
    decision_id: string | null;
    realized_pnl: number | null;
    realized_pnl_pct: number | null;
    alpaca_status: string | null;
    alpaca_order_id: string | null;
    alpaca_submitted_at: string | null;
};

export type TradeInsert = {
    id?: string;
    portfolio_id: string;
    ticker: string;
    signal: string;
    quantity: number;
    price: number;
    total_cost: number;
    executed_at?: string | null;
    decision_id?: string | null;
    realized_pnl?: number | null;
    realized_pnl_pct?: number | null;
    alpaca_status?: string | null;
    alpaca_order_id?: string | null;
    alpaca_submitted_at?: string | null;
};

export type TradeUpdate = {
    id?: string;
    portfolio_id?: string;
    ticker?: string;
    signal?: string;
    quantity?: number;
    price?: number;
    total_cost?: number;
    executed_at?: string | null;
    decision_id?: string | null;
    realized_pnl?: number | null;
    realized_pnl_pct?: number | null;
    alpaca_status?: string | null;
    alpaca_order_id?: string | null;
    alpaca_submitted_at?: string | null;
};

export type Portfolio = {
    id: string;
    owner_id: string;
    cash_balance: number;
    total_equity: number | null;
    buying_power: number | null;
    excess_liquidity: number | null;
    maintenance_margin: number | null;
    last_updated_at: string;
    sma: number | null;
    realized: number | null;
};

export type PortfolioInsert = {
    id?: string;
    owner_id: string;
    cash_balance?: number;
    total_equity?: number | null;
    buying_power?: number | null;
    excess_liquidity?: number | null;
    maintenance_margin?: number | null;
    last_updated_at?: string;
    sma?: number | null;
    realized?: number | null;
};

export type PortfolioUpdate = {
    id?: string;
    owner_id?: string;
    cash_balance?: number;
    total_equity?: number | null;
    buying_power?: number | null;
    excess_liquidity?: number | null;
    maintenance_margin?: number | null;
    last_updated_at?: string;
    sma?: number | null;
    realized?: number | null;
};

export type PortfolioPerformance = {
    id: string;
    portfolio_id: string;
    date: string;
    total_equity: number;
    cash_balance: number;
    buying_power: number;
    sma: number;
    created_at: string;
    initial_margin_req: number | null;
    maintenance_margin_req: number | null;
    available_funds: number | null;
    excess_liquidity: number | null;
    realized: number | null;
};

export type LLMReasoningLog = {
    id: string;
    task_type: string;
    model_provider: string;
    model_name: string;
    prompt: Record<string, any>;
    response: Record<string, any>;
    metadata: Record<string, any>;
    created_at: string | null;
};

export type NewsletterSnapshot = {
    id: string;
    source_id: string;
    chunk_hash: string;
    sender: string;
    subject: string;
    content: string;
    date: string;
    ingested_at: string | null;
};

export type MarketDataCache = {
    ticker: string;
    price: number;
    market_cap: number;
    fetched_at: string | null;
};

export type PositionPnl = {
    position_id: string | null;
    portfolio_id: string | null;
    owner_id: string | null;
    ticker: string | null;
    quantity: number | null;
    average_cost_basis: number | null;
    current_price: number | null;
    price_fetched_at: string | null;
    unrealized_pnl_usd: number | null;
    unrealized_pnl_pct: number | null;
};

export type PortfolioPosition = {
    id: string;
    portfolio_id: string;
    ticker: string;
    quantity: number;
    average_cost_basis: number;
    last_updated_at: string;
};

export type PositionWithReasoning = PositionPnl & { reasoning: string };

export type TradeWithReasoning = Trade & { reasoning: string };

export type MarketFeeling = {
    id: string;
    created_at: string | null;
    updated_at: string | null;
    sentiment_label: string;
    sentiment_emoji: string | null;
    confidence_score: number | null;
    why_explanation: string | null;
    market_direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | null;
    primary_concern: string | null;
    secondary_concern: string | null;
    trades_summary: { buys: number; sells: number; total_value: number } | null;
    lessons_incorporated: number | null;
    memories_incorporated: number | null;
    model_used: string | null;
    processing_time_ms: number | null;
    input_tokens: number | null;
    output_tokens: number | null;
};
