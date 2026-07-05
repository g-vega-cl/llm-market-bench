import type { Database } from './supabase-types';

export type { Database };

type CleanRow<T extends keyof Database['public']['Tables']> = Omit<
    Database['public']['Tables'][T]['Row'],
    'embedding' | 'metadata' | 'prompt' | 'response'
>;

export type Memory = CleanRow<'memories'> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata: Record<string, any> | null;
    similarity?: number;
};

export type MemoryInsert = Omit<
    Database['public']['Tables']['memories']['Insert'],
    'embedding' | 'metadata'
> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata?: Record<string, any> | null;
};

export type MemoryUpdate = Omit<
    Database['public']['Tables']['memories']['Update'],
    'embedding' | 'metadata'
> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata?: Record<string, any> | null;
};

export type Decision = Omit<
    Database['public']['Tables']['decisions']['Row'],
    'embedding' | 'metadata'
> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata: Record<string, any> | null;
};

export type DecisionInsert = Omit<
    Database['public']['Tables']['decisions']['Insert'],
    'embedding' | 'metadata'
> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata?: Record<string, any> | null;
};

export type DecisionUpdate = Omit<
    Database['public']['Tables']['decisions']['Update'],
    'embedding' | 'metadata'
> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata?: Record<string, any> | null;
};

export type Trade = Database['public']['Tables']['trades']['Row'];
export type TradeInsert = Database['public']['Tables']['trades']['Insert'];
export type TradeUpdate = Database['public']['Tables']['trades']['Update'];

export type Portfolio = Database['public']['Tables']['portfolios']['Row'];
export type PortfolioInsert = Database['public']['Tables']['portfolios']['Insert'];
export type PortfolioUpdate = Database['public']['Tables']['portfolios']['Update'];

export type PortfolioPerformance = Database['public']['Tables']['portfolio_performance']['Row'];

export type LLMReasoningLog = Omit<
    Database['public']['Tables']['llm_reasoning_logs']['Row'],
    'prompt' | 'response' | 'metadata'
> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    prompt: Record<string, any>;
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    response: Record<string, any>;
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata: Record<string, any> | null;
};

export type NewsletterSnapshot = Database['public']['Tables']['newsletter_snapshots']['Row'];
export type MarketDataCache = Database['public']['Tables']['market_data_cache']['Row'];
export type MarketFeeling = Database['public']['Tables']['market_feeling']['Row'];
export type MarketBarometer = Database['public']['Tables']['market_barometer_history']['Row'];
export type CorrelationRun = Database['public']['Tables']['correlation_runs']['Row'];
export type CorrelationData = Database['public']['Tables']['correlation_data']['Row'];
export type ConceptMetric = Database['public']['Tables']['concept_metrics']['Row'];
export type SystemAudit = Omit<Database['public']['Tables']['system_audits']['Row'], 'metadata'> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata: Record<string, any> | null;
};

export type PromptExperiment = Omit<
    Database['public']['Tables']['prompt_experiments']['Row'],
    'metrics' | 'research_output'
> & {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metrics: Record<string, any> | null;
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    research_output: Record<string, any> | null;
};

export type PositionPnl = Database['public']['Views']['position_pnl']['Row'];
export type PortfolioPosition = Database['public']['Tables']['portfolio_positions']['Row'];

// Combined / View Model Types
export type PositionWithReasoning = PositionPnl & {
    reasoning?: string;
};

export type TradeWithReasoning = Trade & {
    reasoning?: string;
};

export interface LLMLeaderboardRow {
    model_name: string;
    total_equity: number;
    return_pct: number;
    realized_pnl: number;
    win_rate: number;
    total_trades: number;
    verifier_approval_rate: number | null;
    average_confidence: number;
    api_success_rate: number;
    trading_activity_rate: number;
    trading_performance_score: number;
    reasoning_quality_score: number;
    consistency_score: number;
    composite_score: number;
}
