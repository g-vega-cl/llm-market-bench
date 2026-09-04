import type { ToolTrace } from './chat-types';

export interface ChatToolDefinition {
    type: 'function';
    function: {
        name: string;
        description: string;
        parameters: {
            type: 'object';
            properties: Record<string, unknown>;
            required?: string[];
        };
    };
}

export const SEARCH_MEMORIES_AND_THESES_TOOL: ChatToolDefinition = {
    type: 'function',
    function: {
        name: 'search_memories_and_theses',
        description:
            'Search past agent market memories, lessons learned, causal chains (cause_and_effect), and scenario analyses by ticker or thematic query (e.g. NVO, NVDA, semiconductors, GLP-1, interest rates).',
        parameters: {
            type: 'object',
            properties: {
                ticker: {
                    type: 'string',
                    description: 'Optional ticker symbol (e.g. NVO, NVDA, AAPL).',
                },
                query: {
                    type: 'string',
                    description:
                        'Optional semantic or keyword search term (e.g. "supply chain", "weight loss drugs").',
                },
                limit: {
                    type: 'number',
                    description: 'Maximum number of items to return (default: 5, max: 20).',
                },
            },
        },
    },
};

export const GET_STOCK_CONTEXT_AND_TRADES_TOOL: ChatToolDefinition = {
    type: 'function',
    function: {
        name: 'get_stock_context_and_trades',
        description:
            'Retrieve comprehensive context for a specific stock ticker including recent agent trades, execution prices, buy/sell theses, and model decisions.',
        parameters: {
            type: 'object',
            properties: {
                ticker: {
                    type: 'string',
                    description: 'The stock ticker symbol (e.g. NVO, NVDA, MSFT).',
                },
                limit: {
                    type: 'number',
                    description: 'Number of recent trades/decisions to fetch (default: 10).',
                },
            },
            required: ['ticker'],
        },
    },
};

export const GET_MARKET_SENTIMENT_AND_NEWSLETTER_TOOL: ChatToolDefinition = {
    type: 'function',
    function: {
        name: 'get_market_sentiment_and_newsletter',
        description:
            'Retrieve the latest daily market feeling/sentiment, morning AI newsletter briefing, and macroeconomic overview.',
        parameters: {
            type: 'object',
            properties: {
                limit: {
                    type: 'number',
                    description: 'Number of recent newsletters/sentiment entries (default: 1).',
                },
            },
        },
    },
};

export const QUERY_DATABASE_TABLE_TOOL: ChatToolDefinition = {
    type: 'function',
    function: {
        name: 'query_database_table',
        description:
            'Execute a safe, structured read-only query against any Supabase PostgreSQL table (e.g. trades, portfolios, sector_predictions, prompt_experiments, generated_newsletters, decisions, leaderboard, memories, cause_and_effect, market_feeling).',
        parameters: {
            type: 'object',
            properties: {
                table_name: {
                    type: 'string',
                    description:
                        'Name of the database table to query (e.g. trades, portfolios, sector_predictions, decisions, leaderboard, memories, cause_and_effect).',
                },
                select_columns: {
                    type: 'string',
                    description: 'Comma-separated column names to retrieve (default: "*").',
                },
                filter_column: {
                    type: 'string',
                    description:
                        'Optional column name to filter by (e.g. ticker, model_name, status).',
                },
                filter_value: {
                    type: 'string',
                    description: 'Optional value to match for filter_column.',
                },
                order_by: {
                    type: 'string',
                    description: 'Optional column name to sort results by (e.g. created_at, rank).',
                },
                ascending: {
                    type: 'boolean',
                    description:
                        'Sort direction: true for ascending, false for descending (default: false).',
                },
                limit: {
                    type: 'number',
                    description: 'Maximum number of rows to return (default: 10, max: 50).',
                },
            },
            required: ['table_name'],
        },
    },
};

export const GET_MY_SAVED_THESES_TOOL: ChatToolDefinition = {
    type: 'function',
    function: {
        name: 'get_my_saved_theses',
        description:
            'Retrieve the user’s personal saved research theses and private market notes from their chat_memories. Use this when the user asks about their own saved notes, past theses, or personal insights.',
        parameters: {
            type: 'object',
            properties: {
                ticker: {
                    type: 'string',
                    description:
                        'Optional stock ticker (e.g. NVO, NVDA, AAPL) to filter the user’s private theses.',
                },
                limit: {
                    type: 'number',
                    description:
                        'Maximum number of saved theses to retrieve (default: 5, max: 20).',
                },
            },
        },
    },
};

export const EXPOSED_CHAT_READ_TOOLS: ChatToolDefinition[] = [
    SEARCH_MEMORIES_AND_THESES_TOOL,
    GET_STOCK_CONTEXT_AND_TRADES_TOOL,
    GET_MARKET_SENTIMENT_AND_NEWSLETTER_TOOL,
    GET_MY_SAVED_THESES_TOOL,
    QUERY_DATABASE_TABLE_TOOL,
];

let cachedSchemaSummary: string | null = null;
let cachedSchemaTimestamp = 0;
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

const FALLBACK_SCHEMA_SUMMARY = `Available Database Tables:
- portfolios: id, agent_name, cash, total_equity, updated_at
- trades: id, ticker, action, quantity, price, model_name, thesis, reasoning, created_at
- memories: id, title, content, tickers, tags, importance_score, possible_scenarios, created_at
- cause_and_effect: id, cause, effect, tickers, confidence, horizon, created_at
- market_feeling: id, sentiment, confidence, why_explanation, attempts_summary, created_at
- portfolio_snapshots: id, agent_name, snapshot_date, total_equity, daily_pnl
- sector_predictions: id, prediction_date, target_date, model_name, predicted_sector, status, sector_percentile_score
- prompt_experiments: id, prompt_tag, confidence, track_id, research_reasoning, created_at
- generated_newsletters: id, title, content, created_at
- decisions: id, model_name, ticker, action, thesis, created_at
- leaderboard: rank, model_name, win_rate, return_pct, sharpe_ratio`;

export async function getDatabaseSchemaSummary(supabaseClient: unknown): Promise<string> {
    const now = Date.now();
    if (cachedSchemaSummary && now - cachedSchemaTimestamp < CACHE_TTL_MS) {
        return cachedSchemaSummary;
    }

    try {
        if (supabaseClient && typeof supabaseClient === 'object' && 'from' in supabaseClient) {
            const client = supabaseClient as {
                from: (table: string) => {
                    select: (cols: string) => {
                        limit: (n: number) => Promise<{ data: Record<string, unknown>[] | null }>;
                    };
                };
            };
            const { data: samplePortfolios } = await client.from('portfolios').select('*').limit(1);
            const { data: sampleTrades } = await client.from('trades').select('*').limit(1);

            let dynamicSummary = 'Available Database Tables:\n';
            dynamicSummary += samplePortfolios
                ? `- portfolios: ${Object.keys(samplePortfolios[0] || {}).join(', ') || 'id, agent_name, cash, total_equity, updated_at'}\n`
                : '- portfolios: id, agent_name, cash, total_equity, updated_at\n';
            dynamicSummary += sampleTrades
                ? `- trades: ${Object.keys(sampleTrades[0] || {}).join(', ') || 'id, ticker, action, quantity, price, model_name, thesis, created_at'}\n`
                : '- trades: id, ticker, action, quantity, price, model_name, thesis, created_at\n';
            dynamicSummary += `- memories: id, title, content, tickers, tags, importance_score, possible_scenarios, created_at\n`;
            dynamicSummary += `- cause_and_effect: id, cause, effect, tickers, confidence, horizon, created_at\n`;
            dynamicSummary += `- market_feeling: id, sentiment, confidence, why_explanation, created_at\n`;
            dynamicSummary += `- portfolio_snapshots: id, agent_name, snapshot_date, total_equity, daily_pnl\n`;
            dynamicSummary += `- sector_predictions: id, prediction_date, target_date, model_name, predicted_sector, status\n`;
            dynamicSummary += `- prompt_experiments: id, prompt_tag, confidence, track_id, research_reasoning, created_at\n`;
            dynamicSummary += `- generated_newsletters: id, title, content, created_at\n`;
            dynamicSummary += `- decisions: id, model_name, ticker, action, thesis, created_at\n`;
            dynamicSummary += `- leaderboard: rank, model_name, win_rate, return_pct, sharpe_ratio`;

            cachedSchemaSummary = dynamicSummary;
            cachedSchemaTimestamp = now;
            return dynamicSummary;
        }
    } catch {
        // Fallback on error
    }

    cachedSchemaSummary = FALLBACK_SCHEMA_SUMMARY;
    cachedSchemaTimestamp = now;
    return FALLBACK_SCHEMA_SUMMARY;
}

interface QueryParams {
    tableName: string;
    selectCols: string;
    filterCol: string | null;
    filterVal: unknown;
    orderBy: string;
    ascending: boolean;
    limitCount: number;
}

interface SupabaseGenericQuery {
    eq: (col: string, val: unknown) => SupabaseGenericQuery;
    ilike: (col: string, pattern: string) => SupabaseGenericQuery;
    contains: (col: string, val: unknown) => SupabaseGenericQuery;
    order: (col: string, opts?: { ascending?: boolean }) => SupabaseGenericQuery;
    limit: (n: number) => Promise<{ data: Record<string, unknown>[] | null; error?: unknown }>;
}

async function performSupabaseSelect(
    client: { from: (table: string) => { select: (cols: string) => SupabaseGenericQuery } },
    params: QueryParams,
): Promise<{ data: Record<string, unknown>[] | null; error?: unknown }> {
    let query = client.from(params.tableName).select(params.selectCols);
    if (params.filterCol && params.filterVal !== undefined) {
        query = query.eq(params.filterCol, params.filterVal);
    }
    if (params.orderBy) {
        query = query.order(params.orderBy, { ascending: params.ascending });
    }
    return await query.limit(params.limitCount);
}

export async function executeDatabaseQueryTool(
    args: Record<string, unknown>,
    supabaseClient: unknown,
): Promise<{ result: string; trace: ToolTrace }> {
    const tableName = String(args.table_name || '')
        .trim()
        .toLowerCase();
    if (!tableName) {
        return {
            result: JSON.stringify({ error: 'table_name parameter is required.' }),
            trace: { tool_name: 'query_database_table', summary: 'Missing table_name' },
        };
    }

    const queryParams: QueryParams = {
        tableName,
        selectCols: String(args.select_columns || '*').trim(),
        filterCol: args.filter_column ? String(args.filter_column).trim() : null,
        filterVal: args.filter_value,
        orderBy: args.order_by ? String(args.order_by).trim() : 'created_at',
        ascending: Boolean(args.ascending),
        limitCount: Math.min(Math.max(Number(args.limit) || 10, 1), 50),
    };

    try {
        if (supabaseClient && typeof supabaseClient === 'object' && 'from' in supabaseClient) {
            const client = supabaseClient as {
                from: (table: string) => { select: (cols: string) => SupabaseGenericQuery };
            };
            const res = await performSupabaseSelect(client, queryParams);

            if (res.error) {
                return {
                    result: JSON.stringify({
                        error: `Query failed for table '${tableName}': ${String(res.error)}`,
                    }),
                    trace: {
                        tool_name: 'query_database_table',
                        summary: `Error querying '${tableName}'`,
                    },
                };
            }

            const rows = res.data || [];
            return {
                result: JSON.stringify({ table: tableName, count: rows.length, rows }),
                trace: {
                    tool_name: 'query_database_table',
                    summary: `Queried ${rows.length} rows from '${tableName}'`,
                },
            };
        }

        return {
            result: JSON.stringify({
                table: tableName,
                count: 1,
                rows: [{ note: `Simulated query on '${tableName}'.` }],
            }),
            trace: {
                tool_name: 'query_database_table',
                summary: `Queried '${tableName}'`,
            },
        };
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return {
            result: JSON.stringify({
                error: `Failed to query database table '${tableName}': ${message}`,
            }),
            trace: {
                tool_name: 'query_database_table',
                summary: `Failed to query '${tableName}'`,
            },
        };
    }
}

async function fetchMemoriesAndCausal(
    client: { from: (table: string) => { select: (cols: string) => SupabaseGenericQuery } },
    ticker: string | null,
    query: string | null,
    limit: number,
) {
    let memQuery = client
        .from('memories')
        .select(
            'id, title, content, tickers, tags, importance_score, possible_scenarios, created_at',
        );
    if (ticker) {
        memQuery = memQuery.contains('tickers', [ticker]);
    }
    if (query) {
        memQuery = memQuery.ilike('title', `%${query}%`);
    }
    memQuery = memQuery.order('created_at', { ascending: false });
    const memRes = await memQuery.limit(limit);

    let causalRecords: Record<string, unknown>[] = [];
    if (ticker) {
        const causeQuery = client
            .from('cause_and_effect')
            .select('*')
            .contains('tickers', [ticker])
            .limit(5);
        const causeRes = await causeQuery;
        causalRecords = causeRes.data || [];
    }

    return { memories: memRes.data || [], causalRecords };
}

export async function executeSearchMemoriesTool(
    args: Record<string, unknown>,
    supabaseClient: unknown,
): Promise<{ result: string; trace: ToolTrace }> {
    const ticker = args.ticker ? String(args.ticker).trim().toUpperCase() : null;
    const query = args.query ? String(args.query).trim() : null;
    const limit = Math.min(Math.max(Number(args.limit) || 5, 1), 20);

    try {
        if (supabaseClient && typeof supabaseClient === 'object' && 'from' in supabaseClient) {
            const client = supabaseClient as {
                from: (table: string) => { select: (cols: string) => SupabaseGenericQuery };
            };
            const { memories, causalRecords } = await fetchMemoriesAndCausal(
                client,
                ticker,
                query,
                limit,
            );

            return {
                result: JSON.stringify({
                    ticker,
                    query,
                    memories_found: memories.length,
                    memories,
                    causal_chains: causalRecords,
                }),
                trace: {
                    tool_name: 'search_memories_and_theses',
                    summary: `Retrieved ${memories.length} memories & ${causalRecords.length} causal links${ticker ? ` for ${ticker}` : ''}`,
                },
            };
        }

        return {
            result: JSON.stringify({
                ticker,
                memories_found: 1,
                memories: [
                    {
                        title: `Memory for ${ticker || 'market'}`,
                        content: 'Simulated memory context',
                    },
                ],
                causal_chains: [],
            }),
            trace: {
                tool_name: 'search_memories_and_theses',
                summary: `Retrieved memories for ${ticker || 'market'}`,
            },
        };
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return {
            result: JSON.stringify({ error: `Memory search failed: ${message}` }),
            trace: { tool_name: 'search_memories_and_theses', summary: 'Memory search error' },
        };
    }
}

export async function executeStockContextTool(
    args: Record<string, unknown>,
    supabaseClient: unknown,
): Promise<{ result: string; trace: ToolTrace }> {
    const ticker = String(args.ticker || '')
        .trim()
        .toUpperCase();
    if (!ticker) {
        return {
            result: JSON.stringify({ error: 'ticker parameter is required.' }),
            trace: { tool_name: 'get_stock_context_and_trades', summary: 'Missing ticker' },
        };
    }
    const limit = Math.min(Math.max(Number(args.limit) || 10, 1), 30);

    try {
        if (supabaseClient && typeof supabaseClient === 'object' && 'from' in supabaseClient) {
            const client = supabaseClient as {
                from: (table: string) => { select: (cols: string) => SupabaseGenericQuery };
            };

            const tradesRes = await client
                .from('trades')
                .select(
                    'id, ticker, action, quantity, price, model_name, thesis, reasoning, pnl, created_at',
                )
                .eq('ticker', ticker)
                .order('created_at', { ascending: false })
                .limit(limit);

            const decisionsRes = await client
                .from('decisions')
                .select('id, model_name, ticker, action, thesis, created_at')
                .eq('ticker', ticker)
                .order('created_at', { ascending: false })
                .limit(5);

            const trades = tradesRes.data || [];
            const decisions = decisionsRes.data || [];

            return {
                result: JSON.stringify({
                    ticker,
                    trade_count: trades.length,
                    recent_trades: trades,
                    recent_decisions: decisions,
                }),
                trace: {
                    tool_name: 'get_stock_context_and_trades',
                    summary: `Retrieved ${trades.length} trades & ${decisions.length} decisions for ${ticker}`,
                },
            };
        }

        return {
            result: JSON.stringify({
                ticker,
                trade_count: 1,
                recent_trades: [
                    { ticker, action: 'BUY', price: 150.0, thesis: 'Simulated thesis' },
                ],
            }),
            trace: {
                tool_name: 'get_stock_context_and_trades',
                summary: `Retrieved context for ${ticker}`,
            },
        };
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return {
            result: JSON.stringify({ error: `Stock context retrieval failed: ${message}` }),
            trace: {
                tool_name: 'get_stock_context_and_trades',
                summary: `Error fetching ${ticker}`,
            },
        };
    }
}

export async function executeMarketSentimentTool(
    args: Record<string, unknown>,
    supabaseClient: unknown,
): Promise<{ result: string; trace: ToolTrace }> {
    const limit = Math.min(Math.max(Number(args.limit) || 1, 1), 5);

    try {
        if (supabaseClient && typeof supabaseClient === 'object' && 'from' in supabaseClient) {
            const client = supabaseClient as {
                from: (table: string) => { select: (cols: string) => SupabaseGenericQuery };
            };

            const sentimentRes = await client
                .from('market_feeling')
                .select('id, sentiment, confidence, why_explanation, created_at')
                .order('created_at', { ascending: false })
                .limit(limit);

            const newsletterRes = await client
                .from('generated_newsletters')
                .select('id, title, content, created_at')
                .order('created_at', { ascending: false })
                .limit(limit);

            const sentiment = sentimentRes.data || [];
            const newsletters = newsletterRes.data || [];

            return {
                result: JSON.stringify({
                    market_feeling: sentiment[0] || null,
                    latest_newsletter: newsletters[0] || null,
                }),
                trace: {
                    tool_name: 'get_market_sentiment_and_newsletter',
                    summary: `Retrieved latest market feeling (${sentiment[0]?.sentiment || 'N/A'}) & morning briefing`,
                },
            };
        }

        return {
            result: JSON.stringify({
                market_feeling: { sentiment: 'BULLISH', confidence: 0.8 },
                latest_newsletter: { title: 'Daily Briefing' },
            }),
            trace: {
                tool_name: 'get_market_sentiment_and_newsletter',
                summary: 'Retrieved market feeling & briefing',
            },
        };
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return {
            result: JSON.stringify({ error: `Market sentiment retrieval failed: ${message}` }),
            trace: {
                tool_name: 'get_market_sentiment_and_newsletter',
                summary: 'Sentiment fetch error',
            },
        };
    }
}

async function fetchChatMemoriesFromDb(
    client: { from: (table: string) => { select: (cols: string) => SupabaseGenericQuery } },
    userId: string | undefined,
    ticker: string | null,
    limit: number,
): Promise<Record<string, unknown>[]> {
    let query = client
        .from('chat_memories')
        .select('id, ticker, thesis, tags, importance_score, created_at');

    if (userId) {
        query = query.eq('user_id', userId);
    }
    if (ticker) {
        query = query.eq('ticker', ticker);
    }

    query = query.order('created_at', { ascending: false });
    const res = await query.limit(limit);
    return (res as { data: Record<string, unknown>[] | null }).data || [];
}

export async function executeGetMySavedThesesTool(
    args: Record<string, unknown>,
    supabaseClient: unknown,
    userId?: string,
): Promise<{ result: string; trace: ToolTrace }> {
    const ticker = args.ticker ? String(args.ticker).trim().toUpperCase() : null;
    const limit = Math.min(Math.max(Number(args.limit) || 5, 1), 20);

    try {
        if (supabaseClient && typeof supabaseClient === 'object' && 'from' in supabaseClient) {
            const client = supabaseClient as {
                from: (table: string) => { select: (cols: string) => SupabaseGenericQuery };
            };
            const data = await fetchChatMemoriesFromDb(client, userId, ticker, limit);

            return {
                result: JSON.stringify({
                    theses: data,
                    count: data.length,
                    ticker,
                }),
                trace: {
                    tool_name: 'get_my_saved_theses',
                    summary: `Retrieved ${data.length} saved thesis${data.length === 1 ? '' : 'es'}${ticker ? ` for ${ticker}` : ''}`,
                },
            };
        }

        return {
            result: JSON.stringify({ theses: [], count: 0, ticker }),
            trace: {
                tool_name: 'get_my_saved_theses',
                summary: 'No saved theses found',
            },
        };
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return {
            result: JSON.stringify({ error: `Failed to retrieve saved theses: ${message}` }),
            trace: {
                tool_name: 'get_my_saved_theses',
                summary: 'Error retrieving saved theses',
            },
        };
    }
}

type ToolExecutor = (
    args: Record<string, unknown>,
    supabaseClient: unknown,
    userId?: string,
) => Promise<{ result: string; trace: ToolTrace }>;

const TOOL_EXECUTORS: Record<string, ToolExecutor> = {
    search_memories_and_theses: (args, client) => executeSearchMemoriesTool(args, client),
    get_stock_context_and_trades: (args, client) => executeStockContextTool(args, client),
    get_market_sentiment_and_newsletter: (args, client) => executeMarketSentimentTool(args, client),
    get_my_saved_theses: (args, client, userId) =>
        executeGetMySavedThesesTool(args, client, userId),
};

export async function executeChatTool(
    toolName: string,
    args: Record<string, unknown>,
    supabaseClient: unknown,
    userId?: string,
): Promise<{ result: string; trace: ToolTrace }> {
    const executor = TOOL_EXECUTORS[toolName];
    if (executor) {
        return await executor(args, supabaseClient, userId);
    }
    return await executeDatabaseQueryTool(args, supabaseClient);
}
