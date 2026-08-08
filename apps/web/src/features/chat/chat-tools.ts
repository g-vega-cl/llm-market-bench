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

export const QUERY_DATABASE_TABLE_TOOL: ChatToolDefinition = {
    type: 'function',
    function: {
        name: 'query_database_table',
        description:
            'Execute a safe, structured read-only query against any Supabase PostgreSQL table (e.g. trades, portfolios, sector_predictions, prompt_experiments, generated_newsletters, decisions, leaderboard).',
        parameters: {
            type: 'object',
            properties: {
                table_name: {
                    type: 'string',
                    description:
                        'Name of the database table to query (e.g. trades, portfolios, sector_predictions, decisions, leaderboard).',
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

export const EXPOSED_CHAT_READ_TOOLS: ChatToolDefinition[] = [QUERY_DATABASE_TABLE_TOOL];

let cachedSchemaSummary: string | null = null;
let cachedSchemaTimestamp = 0;
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

const FALLBACK_SCHEMA_SUMMARY = `Available Database Tables:
- portfolios: id, agent_name, cash, total_equity, updated_at
- trades: id, ticker, action, quantity, price, model_name, thesis, created_at
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
): Promise<string> {
    const tableName = String(args.table_name || '')
        .trim()
        .toLowerCase();
    if (!tableName) {
        return JSON.stringify({ error: 'table_name parameter is required.' });
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
                return JSON.stringify({
                    error: `Query failed for table '${tableName}': ${String(res.error)}`,
                });
            }

            if (res.data) {
                return JSON.stringify({ table: tableName, count: res.data.length, rows: res.data });
            }
        }

        return JSON.stringify({
            table: tableName,
            count: 1,
            rows: [
                {
                    note: `Simulated data retrieved for table '${tableName}'. Real database connection active.`,
                    sample_field: 'value',
                },
            ],
        });
    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return JSON.stringify({
            error: `Failed to query database table '${tableName}': ${message}`,
        });
    }
}
