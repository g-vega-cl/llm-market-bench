export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
    // Allows to automatically instantiate createClient with right options
    // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
    __InternalSupabase: {
        PostgrestVersion: '14.1';
    };
    graphql_public: {
        Tables: {
            [_ in never]: never;
        };
        Views: {
            [_ in never]: never;
        };
        Functions: {
            graphql: {
                Args: {
                    extensions?: Json;
                    operationName?: string;
                    query?: string;
                    variables?: Json;
                };
                Returns: Json;
            };
        };
        Enums: {
            [_ in never]: never;
        };
        CompositeTypes: {
            [_ in never]: never;
        };
    };
    public: {
        Tables: {
            cause_and_effect: {
                Row: {
                    analysis: string;
                    confidence: number | null;
                    created_at: string | null;
                    event_id: string;
                    id: string;
                    market_outcome: string | null;
                    tags: string[] | null;
                };
                Insert: {
                    analysis: string;
                    confidence?: number | null;
                    created_at?: string | null;
                    event_id: string;
                    id?: string;
                    market_outcome?: string | null;
                    tags?: string[] | null;
                };
                Update: {
                    analysis?: string;
                    confidence?: number | null;
                    created_at?: string | null;
                    event_id?: string;
                    id?: string;
                    market_outcome?: string | null;
                    tags?: string[] | null;
                };
                Relationships: [
                    {
                        foreignKeyName: 'cause_and_effect_event_id_fkey';
                        columns: ['event_id'];
                        isOneToOne: false;
                        referencedRelation: 'memories';
                        referencedColumns: ['id'];
                    },
                ];
            };
            concept_metrics: {
                Row: {
                    concept_name: string;
                    concept_vector: string;
                    created_at: string | null;
                    first_mention_at: string | null;
                    id: string;
                    last_mention_at: string | null;
                    mention_count: number | null;
                    pca_x: number | null;
                    pca_y: number | null;
                    updated_at: string | null;
                    velocity_score: number | null;
                };
                Insert: {
                    concept_name: string;
                    concept_vector: string;
                    created_at?: string | null;
                    first_mention_at?: string | null;
                    id?: string;
                    last_mention_at?: string | null;
                    mention_count?: number | null;
                    pca_x?: number | null;
                    pca_y?: number | null;
                    updated_at?: string | null;
                    velocity_score?: number | null;
                };
                Update: {
                    concept_name?: string;
                    concept_vector?: string;
                    created_at?: string | null;
                    first_mention_at?: string | null;
                    id?: string;
                    last_mention_at?: string | null;
                    mention_count?: number | null;
                    pca_x?: number | null;
                    pca_y?: number | null;
                    updated_at?: string | null;
                    velocity_score?: number | null;
                };
                Relationships: [];
            };
            correlation_data: {
                Row: {
                    data_points: number | null;
                    id: string;
                    pearson_corr: number | null;
                    returns_a_90d: number | null;
                    returns_b_90d: number | null;
                    run_id: string;
                    spearman_corr: number | null;
                    ticker_a: string;
                    ticker_b: string;
                };
                Insert: {
                    data_points?: number | null;
                    id?: string;
                    pearson_corr?: number | null;
                    returns_a_90d?: number | null;
                    returns_b_90d?: number | null;
                    run_id: string;
                    spearman_corr?: number | null;
                    ticker_a: string;
                    ticker_b: string;
                };
                Update: {
                    data_points?: number | null;
                    id?: string;
                    pearson_corr?: number | null;
                    returns_a_90d?: number | null;
                    returns_b_90d?: number | null;
                    run_id?: string;
                    spearman_corr?: number | null;
                    ticker_a?: string;
                    ticker_b?: string;
                };
                Relationships: [
                    {
                        foreignKeyName: 'correlation_data_run_id_fkey';
                        columns: ['run_id'];
                        isOneToOne: false;
                        referencedRelation: 'correlation_runs';
                        referencedColumns: ['id'];
                    },
                ];
            };
            correlation_runs: {
                Row: {
                    created_at: string | null;
                    id: string;
                    num_assets: number;
                    run_date: string;
                    tickers: Json;
                    window_days: number;
                };
                Insert: {
                    created_at?: string | null;
                    id?: string;
                    num_assets: number;
                    run_date: string;
                    tickers: Json;
                    window_days?: number;
                };
                Update: {
                    created_at?: string | null;
                    id?: string;
                    num_assets?: number;
                    run_date?: string;
                    tickers?: Json;
                    window_days?: number;
                };
                Relationships: [];
            };
            decisions: {
                Row: {
                    confidence: number;
                    created_at: string | null;
                    embedding: string | null;
                    id: string;
                    limit_price: number | null;
                    metadata: Json | null;
                    model_name: string;
                    model_provider: string;
                    price: number | null;
                    reasoning: string;
                    signal: string;
                    source_id: string;
                    status: string | null;
                    ticker: string;
                    trade_id: string | null;
                };
                Insert: {
                    confidence: number;
                    created_at?: string | null;
                    embedding?: string | null;
                    id?: string;
                    limit_price?: number | null;
                    metadata?: Json | null;
                    model_name: string;
                    model_provider: string;
                    price?: number | null;
                    reasoning: string;
                    signal: string;
                    source_id: string;
                    status?: string | null;
                    ticker: string;
                    trade_id?: string | null;
                };
                Update: {
                    confidence?: number;
                    created_at?: string | null;
                    embedding?: string | null;
                    id?: string;
                    limit_price?: number | null;
                    metadata?: Json | null;
                    model_name?: string;
                    model_provider?: string;
                    price?: number | null;
                    reasoning?: string;
                    signal?: string;
                    source_id?: string;
                    status?: string | null;
                    ticker?: string;
                    trade_id?: string | null;
                };
                Relationships: [
                    {
                        foreignKeyName: 'decisions_trade_id_fkey';
                        columns: ['trade_id'];
                        isOneToOne: false;
                        referencedRelation: 'trades';
                        referencedColumns: ['id'];
                    },
                ];
            };
            ingestion_logs: {
                Row: {
                    created_at: string | null;
                    id: string;
                    log_blob: string;
                    run_date: string;
                    run_id: string;
                    run_number: number;
                };
                Insert: {
                    created_at?: string | null;
                    id?: string;
                    log_blob: string;
                    run_date: string;
                    run_id: string;
                    run_number: number;
                };
                Update: {
                    created_at?: string | null;
                    id?: string;
                    log_blob?: string;
                    run_date?: string;
                    run_id?: string;
                    run_number?: number;
                };
                Relationships: [];
            };
            llm_reasoning_logs: {
                Row: {
                    created_at: string | null;
                    id: string;
                    metadata: Json | null;
                    model_name: string;
                    model_provider: string;
                    prompt: Json;
                    response: Json | null;
                    task_type: string;
                };
                Insert: {
                    created_at?: string | null;
                    id?: string;
                    metadata?: Json | null;
                    model_name: string;
                    model_provider: string;
                    prompt: Json;
                    response?: Json | null;
                    task_type: string;
                };
                Update: {
                    created_at?: string | null;
                    id?: string;
                    metadata?: Json | null;
                    model_name?: string;
                    model_provider?: string;
                    prompt?: Json;
                    response?: Json | null;
                    task_type?: string;
                };
                Relationships: [];
            };
            market_data_cache: {
                Row: {
                    fetched_at: string | null;
                    market_cap: number;
                    price: number;
                    regime_flag: string | null;
                    stdev_pct: number | null;
                    ticker: string;
                    today_pct_change: number | null;
                };
                Insert: {
                    fetched_at?: string | null;
                    market_cap: number;
                    price: number;
                    regime_flag?: string | null;
                    stdev_pct?: number | null;
                    ticker: string;
                    today_pct_change?: number | null;
                };
                Update: {
                    fetched_at?: string | null;
                    market_cap?: number;
                    price?: number;
                    regime_flag?: string | null;
                    stdev_pct?: number | null;
                    ticker?: string;
                    today_pct_change?: number | null;
                };
                Relationships: [];
            };
            market_feeling: {
                Row: {
                    attempts_summary: Json | null;
                    confidence_score: number | null;
                    created_at: string | null;
                    id: string;
                    input_tokens: number | null;
                    lessons_incorporated: number | null;
                    market_direction: string | null;
                    memories_incorporated: number | null;
                    model_used: string | null;
                    output_tokens: number | null;
                    primary_concern: string | null;
                    processing_time_ms: number | null;
                    secondary_concern: string | null;
                    sentiment_emoji: string | null;
                    sentiment_label: string;
                    trades_summary: Json | null;
                    updated_at: string | null;
                    why_explanation: string | null;
                };
                Insert: {
                    attempts_summary?: Json | null;
                    confidence_score?: number | null;
                    created_at?: string | null;
                    id?: string;
                    input_tokens?: number | null;
                    lessons_incorporated?: number | null;
                    market_direction?: string | null;
                    memories_incorporated?: number | null;
                    model_used?: string | null;
                    output_tokens?: number | null;
                    primary_concern?: string | null;
                    processing_time_ms?: number | null;
                    secondary_concern?: string | null;
                    sentiment_emoji?: string | null;
                    sentiment_label: string;
                    trades_summary?: Json | null;
                    updated_at?: string | null;
                    why_explanation?: string | null;
                };
                Update: {
                    attempts_summary?: Json | null;
                    confidence_score?: number | null;
                    created_at?: string | null;
                    id?: string;
                    input_tokens?: number | null;
                    lessons_incorporated?: number | null;
                    market_direction?: string | null;
                    memories_incorporated?: number | null;
                    model_used?: string | null;
                    output_tokens?: number | null;
                    primary_concern?: string | null;
                    processing_time_ms?: number | null;
                    secondary_concern?: string | null;
                    sentiment_emoji?: string | null;
                    sentiment_label?: string;
                    trades_summary?: Json | null;
                    updated_at?: string | null;
                    why_explanation?: string | null;
                };
                Relationships: [];
            };
            memories: {
                Row: {
                    content: string;
                    created_at: string | null;
                    embedding: string | null;
                    id: string;
                    importance_score: number | null;
                    memory_type: string | null;
                    metadata: Json | null;
                    parent_id: string | null;
                    relationship_type: string | null;
                    relevance_score: number | null;
                    status: string | null;
                    target_date: string | null;
                };
                Insert: {
                    content: string;
                    created_at?: string | null;
                    embedding?: string | null;
                    id?: string;
                    importance_score?: number | null;
                    memory_type?: string | null;
                    metadata?: Json | null;
                    parent_id?: string | null;
                    relationship_type?: string | null;
                    relevance_score?: number | null;
                    status?: string | null;
                    target_date?: string | null;
                };
                Update: {
                    content?: string;
                    created_at?: string | null;
                    embedding?: string | null;
                    id?: string;
                    importance_score?: number | null;
                    memory_type?: string | null;
                    metadata?: Json | null;
                    parent_id?: string | null;
                    relationship_type?: string | null;
                    relevance_score?: number | null;
                    status?: string | null;
                    target_date?: string | null;
                };
                Relationships: [
                    {
                        foreignKeyName: 'memories_parent_id_fkey';
                        columns: ['parent_id'];
                        isOneToOne: false;
                        referencedRelation: 'memories';
                        referencedColumns: ['id'];
                    },
                ];
            };
            newsletter_snapshots: {
                Row: {
                    chunk_hash: string;
                    content: string;
                    date: string;
                    id: string;
                    ingested_at: string | null;
                    sender: string;
                    source_id: string;
                    subject: string;
                };
                Insert: {
                    chunk_hash: string;
                    content: string;
                    date: string;
                    id?: string;
                    ingested_at?: string | null;
                    sender: string;
                    source_id: string;
                    subject: string;
                };
                Update: {
                    chunk_hash?: string;
                    content?: string;
                    date?: string;
                    id?: string;
                    ingested_at?: string | null;
                    sender?: string;
                    source_id?: string;
                    subject?: string;
                };
                Relationships: [];
            };
            portfolio_performance: {
                Row: {
                    available_funds: number | null;
                    buying_power: number;
                    cash_balance: number;
                    created_at: string;
                    date: string;
                    excess_liquidity: number | null;
                    id: string;
                    initial_margin_req: number | null;
                    maintenance_margin_req: number | null;
                    portfolio_id: string;
                    realized: number | null;
                    sma: number;
                    total_equity: number;
                };
                Insert: {
                    available_funds?: number | null;
                    buying_power: number;
                    cash_balance: number;
                    created_at?: string;
                    date?: string;
                    excess_liquidity?: number | null;
                    id?: string;
                    initial_margin_req?: number | null;
                    maintenance_margin_req?: number | null;
                    portfolio_id: string;
                    realized?: number | null;
                    sma: number;
                    total_equity: number;
                };
                Update: {
                    available_funds?: number | null;
                    buying_power?: number;
                    cash_balance?: number;
                    created_at?: string;
                    date?: string;
                    excess_liquidity?: number | null;
                    id?: string;
                    initial_margin_req?: number | null;
                    maintenance_margin_req?: number | null;
                    portfolio_id?: string;
                    realized?: number | null;
                    sma?: number;
                    total_equity?: number;
                };
                Relationships: [
                    {
                        foreignKeyName: 'portfolio_performance_portfolio_id_fkey';
                        columns: ['portfolio_id'];
                        isOneToOne: false;
                        referencedRelation: 'portfolios';
                        referencedColumns: ['id'];
                    },
                ];
            };
            portfolio_positions: {
                Row: {
                    average_cost_basis: number;
                    id: string;
                    last_updated_at: string;
                    portfolio_id: string;
                    quantity: number;
                    ticker: string;
                };
                Insert: {
                    average_cost_basis: number;
                    id?: string;
                    last_updated_at?: string;
                    portfolio_id: string;
                    quantity: number;
                    ticker: string;
                };
                Update: {
                    average_cost_basis?: number;
                    id?: string;
                    last_updated_at?: string;
                    portfolio_id?: string;
                    quantity?: number;
                    ticker?: string;
                };
                Relationships: [
                    {
                        foreignKeyName: 'portfolio_positions_portfolio_id_fkey';
                        columns: ['portfolio_id'];
                        isOneToOne: false;
                        referencedRelation: 'portfolios';
                        referencedColumns: ['id'];
                    },
                ];
            };
            portfolios: {
                Row: {
                    buying_power: number | null;
                    cash_balance: number;
                    excess_liquidity: number | null;
                    id: string;
                    last_updated_at: string;
                    maintenance_margin: number | null;
                    owner_id: string;
                    realized: number | null;
                    sma: number | null;
                    total_equity: number | null;
                };
                Insert: {
                    buying_power?: number | null;
                    cash_balance?: number;
                    excess_liquidity?: number | null;
                    id?: string;
                    last_updated_at?: string;
                    maintenance_margin?: number | null;
                    owner_id: string;
                    realized?: number | null;
                    sma?: number | null;
                    total_equity?: number | null;
                };
                Update: {
                    buying_power?: number | null;
                    cash_balance?: number;
                    excess_liquidity?: number | null;
                    id?: string;
                    last_updated_at?: string;
                    maintenance_margin?: number | null;
                    owner_id?: string;
                    realized?: number | null;
                    sma?: number | null;
                    total_equity?: number | null;
                };
                Relationships: [];
            };
            price_history: {
                Row: {
                    fetched_at: string | null;
                    market_cap: number | null;
                    price: number;
                    ticker: string;
                };
                Insert: {
                    fetched_at?: string | null;
                    market_cap?: number | null;
                    price: number;
                    ticker: string;
                };
                Update: {
                    fetched_at?: string | null;
                    market_cap?: number | null;
                    price?: number;
                    ticker?: string;
                };
                Relationships: [];
            };
            prompt_experiments: {
                Row: {
                    change_description: string | null;
                    created_at: string;
                    experiment_type: string;
                    id: string;
                    metrics: Json | null;
                    parent_tag: string | null;
                    prompt_content: string;
                    prompt_name: string;
                    research_output: Json | null;
                    status: string;
                    variant_tag: string;
                    week_end: string;
                    week_start: string;
                };
                Insert: {
                    change_description?: string | null;
                    created_at?: string;
                    experiment_type?: string;
                    id?: string;
                    metrics?: Json | null;
                    parent_tag?: string | null;
                    prompt_content: string;
                    prompt_name?: string;
                    research_output?: Json | null;
                    status?: string;
                    variant_tag: string;
                    week_end: string;
                    week_start: string;
                };
                Update: {
                    change_description?: string | null;
                    created_at?: string;
                    experiment_type?: string;
                    id?: string;
                    metrics?: Json | null;
                    parent_tag?: string | null;
                    prompt_content?: string;
                    prompt_name?: string;
                    research_output?: Json | null;
                    status?: string;
                    variant_tag?: string;
                    week_end?: string;
                    week_start?: string;
                };
                Relationships: [
                    {
                        foreignKeyName: 'prompt_experiments_parent_tag_fkey';
                        columns: ['parent_tag'];
                        isOneToOne: false;
                        referencedRelation: 'prompt_experiments';
                        referencedColumns: ['variant_tag'];
                    },
                ];
            };
            system_audits: {
                Row: {
                    analysis_method: string | null;
                    audit_run_id: string | null;
                    audit_type: string;
                    created_at: string | null;
                    created_by: string | null;
                    description: string;
                    id: string;
                    metadata: Json | null;
                    resolved_at: string | null;
                    resolved_by: string | null;
                    severity: string;
                    source_id: string | null;
                    source_table: string | null;
                    status: string | null;
                    suggestion: string | null;
                    title: string;
                };
                Insert: {
                    analysis_method?: string | null;
                    audit_run_id?: string | null;
                    audit_type: string;
                    created_at?: string | null;
                    created_by?: string | null;
                    description: string;
                    id?: string;
                    metadata?: Json | null;
                    resolved_at?: string | null;
                    resolved_by?: string | null;
                    severity: string;
                    source_id?: string | null;
                    source_table?: string | null;
                    status?: string | null;
                    suggestion?: string | null;
                    title: string;
                };
                Update: {
                    analysis_method?: string | null;
                    audit_run_id?: string | null;
                    audit_type?: string;
                    created_at?: string | null;
                    created_by?: string | null;
                    description?: string;
                    id?: string;
                    metadata?: Json | null;
                    resolved_at?: string | null;
                    resolved_by?: string | null;
                    severity?: string;
                    source_id?: string | null;
                    source_table?: string | null;
                    status?: string | null;
                    suggestion?: string | null;
                    title?: string;
                };
                Relationships: [];
            };
            trades: {
                Row: {
                    alpaca_filled_at: string | null;
                    alpaca_order_id: string | null;
                    alpaca_status: string | null;
                    alpaca_submitted_at: string | null;
                    decision_id: string | null;
                    executed_at: string | null;
                    id: string;
                    portfolio_id: string;
                    price: number;
                    quantity: number;
                    realized_pnl: number | null;
                    realized_pnl_pct: number | null;
                    reasoning: string | null;
                    signal: string;
                    ticker: string;
                    total_cost: number;
                };
                Insert: {
                    alpaca_filled_at?: string | null;
                    alpaca_order_id?: string | null;
                    alpaca_status?: string | null;
                    alpaca_submitted_at?: string | null;
                    decision_id?: string | null;
                    executed_at?: string | null;
                    id?: string;
                    portfolio_id: string;
                    price: number;
                    quantity: number;
                    realized_pnl?: number | null;
                    realized_pnl_pct?: number | null;
                    reasoning?: string | null;
                    signal: string;
                    ticker: string;
                    total_cost: number;
                };
                Update: {
                    alpaca_filled_at?: string | null;
                    alpaca_order_id?: string | null;
                    alpaca_status?: string | null;
                    alpaca_submitted_at?: string | null;
                    decision_id?: string | null;
                    executed_at?: string | null;
                    id?: string;
                    portfolio_id?: string;
                    price?: number;
                    quantity?: number;
                    realized_pnl?: number | null;
                    realized_pnl_pct?: number | null;
                    reasoning?: string | null;
                    signal?: string;
                    ticker?: string;
                    total_cost?: number;
                };
                Relationships: [
                    {
                        foreignKeyName: 'trades_portfolio_id_fkey';
                        columns: ['portfolio_id'];
                        isOneToOne: false;
                        referencedRelation: 'portfolios';
                        referencedColumns: ['id'];
                    },
                ];
            };
        };
        Views: {
            position_pnl: {
                Row: {
                    average_cost_basis: number | null;
                    current_price: number | null;
                    owner_id: string | null;
                    portfolio_id: string | null;
                    position_id: string | null;
                    price_fetched_at: string | null;
                    quantity: number | null;
                    ticker: string | null;
                    unrealized_pnl_pct: number | null;
                    unrealized_pnl_usd: number | null;
                };
                Relationships: [
                    {
                        foreignKeyName: 'portfolio_positions_portfolio_id_fkey';
                        columns: ['portfolio_id'];
                        isOneToOne: false;
                        referencedRelation: 'portfolios';
                        referencedColumns: ['id'];
                    },
                ];
            };
        };
        Functions: {
            cleanup_old_correlation_runs: { Args: never; Returns: undefined };
            cleanup_old_market_feelings: { Args: never; Returns: undefined };
            exec_sql: {
                Args: { query: string };
                Returns: {
                    result: Json;
                }[];
            };
            match_concepts: {
                Args: {
                    match_count: number;
                    match_threshold: number;
                    query_embedding: string;
                };
                Returns: {
                    concept_name: string;
                    id: string;
                    mention_count: number;
                    similarity: number;
                }[];
            };
            match_decisions: {
                Args: {
                    filter_model_name?: string;
                    match_count: number;
                    match_threshold: number;
                    query_embedding: string;
                };
                Returns: {
                    id: string;
                    model_name: string;
                    reasoning: string;
                    signal: string;
                    similarity: number;
                    ticker: string;
                }[];
            };
            match_memories: {
                Args: {
                    filter_memory_types?: string[];
                    match_count: number;
                    match_threshold: number;
                    query_embedding: string;
                };
                Returns: {
                    content: string;
                    id: string;
                    importance_score: number;
                    memory_type: string;
                    metadata: Json;
                    similarity: number;
                }[];
            };
            match_memories_with_time: {
                Args: {
                    match_count: number;
                    match_threshold: number;
                    min_time: string;
                    query_embedding: string;
                };
                Returns: {
                    content: string;
                    created_at: string;
                    id: string;
                    metadata: Json;
                    similarity: number;
                }[];
            };
        };
        Enums: {
            [_ in never]: never;
        };
        CompositeTypes: {
            [_ in never]: never;
        };
    };
};

type DatabaseWithoutInternals = Omit<Database, '__InternalSupabase'>;

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, 'public'>];

export type Tables<
    DefaultSchemaTableNameOrOptions extends
        | keyof (DefaultSchema['Tables'] & DefaultSchema['Views'])
        | { schema: keyof DatabaseWithoutInternals },
    TableName extends DefaultSchemaTableNameOrOptions extends {
        schema: keyof DatabaseWithoutInternals;
    }
        ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'] &
              DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Views'])
        : never = never,
> = DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
}
    ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'] &
          DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Views'])[TableName] extends {
          Row: infer R;
      }
        ? R
        : never
    : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema['Tables'] &
            DefaultSchema['Views'])
      ? (DefaultSchema['Tables'] &
            DefaultSchema['Views'])[DefaultSchemaTableNameOrOptions] extends {
            Row: infer R;
        }
          ? R
          : never
      : never;

export type TablesInsert<
    DefaultSchemaTableNameOrOptions extends
        | keyof DefaultSchema['Tables']
        | { schema: keyof DatabaseWithoutInternals },
    TableName extends DefaultSchemaTableNameOrOptions extends {
        schema: keyof DatabaseWithoutInternals;
    }
        ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables']
        : never = never,
> = DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
}
    ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'][TableName] extends {
          Insert: infer I;
      }
        ? I
        : never
    : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema['Tables']
      ? DefaultSchema['Tables'][DefaultSchemaTableNameOrOptions] extends {
            Insert: infer I;
        }
          ? I
          : never
      : never;

export type TablesUpdate<
    DefaultSchemaTableNameOrOptions extends
        | keyof DefaultSchema['Tables']
        | { schema: keyof DatabaseWithoutInternals },
    TableName extends DefaultSchemaTableNameOrOptions extends {
        schema: keyof DatabaseWithoutInternals;
    }
        ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables']
        : never = never,
> = DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
}
    ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'][TableName] extends {
          Update: infer U;
      }
        ? U
        : never
    : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema['Tables']
      ? DefaultSchema['Tables'][DefaultSchemaTableNameOrOptions] extends {
            Update: infer U;
        }
          ? U
          : never
      : never;

export type Enums<
    DefaultSchemaEnumNameOrOptions extends
        | keyof DefaultSchema['Enums']
        | { schema: keyof DatabaseWithoutInternals },
    EnumName extends DefaultSchemaEnumNameOrOptions extends {
        schema: keyof DatabaseWithoutInternals;
    }
        ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions['schema']]['Enums']
        : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
}
    ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions['schema']]['Enums'][EnumName]
    : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema['Enums']
      ? DefaultSchema['Enums'][DefaultSchemaEnumNameOrOptions]
      : never;

export type CompositeTypes<
    PublicCompositeTypeNameOrOptions extends
        | keyof DefaultSchema['CompositeTypes']
        | { schema: keyof DatabaseWithoutInternals },
    CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
        schema: keyof DatabaseWithoutInternals;
    }
        ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions['schema']]['CompositeTypes']
        : never = never,
> = PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
}
    ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions['schema']]['CompositeTypes'][CompositeTypeName]
    : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema['CompositeTypes']
      ? DefaultSchema['CompositeTypes'][PublicCompositeTypeNameOrOptions]
      : never;

export const Constants = {
    graphql_public: {
        Enums: {},
    },
    public: {
        Enums: {},
    },
} as const;
