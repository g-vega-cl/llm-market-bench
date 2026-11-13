import { beforeEach, describe, expect, it, vi } from 'vitest';
import { handleChatMessage } from './chat-server';
import { executeDatabaseQueryTool, getDatabaseSchemaSummary } from './chat-tools';

// Mock Supabase Server Client
const mockGetUser = vi.fn();
const mockFrom = vi.fn();
vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({
        auth: {
            getUser: mockGetUser,
        },
    }),
}));

vi.mock('~/lib/db', () => ({
    getDbServerClient: () => ({
        from: mockFrom,
    }),
    getDbAdminClient: () => ({
        from: mockFrom,
    }),
}));

describe('Chat Server Handler (handleChatMessage)', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        vi.clearAllMocks();
        global.fetch = vi.fn();
        process.env = { ...originalEnv, DEEPSEEK_API_KEY: 'test-deepseek-key' };
    });

    it('should reject unauthenticated users with 403 Forbidden', async () => {
        mockGetUser.mockResolvedValue({ data: { user: null }, error: null });

        await expect(
            handleChatMessage({
                messages: [{ role: 'user', content: 'Hello' }],
            }),
        ).rejects.toThrow('Authentication required');
    });

    it('should reject non-allowed email users with 403 Forbidden', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { email: 'unauthorized@example.com' } },
            error: null,
        });

        await expect(
            handleChatMessage({
                messages: [{ role: 'user', content: 'Hello' }],
            }),
        ).rejects.toThrow('Chat feature is restricted to authorized accounts');
    });

    it('should pass query_database_table tool and system prompt with schema summary', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { email: 'g.vega.cl@gmail.com' } },
            error: null,
        });

        const mockDeepSeekResponse = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content: 'Hello Cesar! How can I help you analyze database records today?',
                    },
                },
            ],
        };

        (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
            ok: true,
            json: async () => mockDeepSeekResponse,
        });

        const result = await handleChatMessage({
            messages: [{ role: 'user', content: 'Hello' }],
        });

        expect(global.fetch).toHaveBeenCalledTimes(1);
        const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);

        expect(body.tools).toBeDefined();
        const toolNames = body.tools.map((t: { function: { name: string } }) => t.function.name);
        expect(toolNames).toContain('query_database_table');
        expect(toolNames).toContain('search_memories_and_theses');
        expect(toolNames).toContain('get_stock_context_and_trades');

        // Verify system prompt includes database table catalog including gov/macro tables
        expect(body.messages[0].role).toBe('system');
        expect(body.messages[0].content).toContain('Available Database Tables:');
        expect(body.messages[0].content).toContain('gov_macro_liquidity');
        expect(body.messages[0].content).toContain('gov_contracts');
        expect(body.messages[0].content).toContain('congress_trades');
        expect(body.messages[0].content).toContain('insider_trades');
        expect(body.messages[0].content).toContain('institutional_whale_stakes');
        expect(body.messages[0].content).toContain('fred_series_cache');

        expect(result).toEqual({
            role: 'assistant',
            content: 'Hello Cesar! How can I help you analyze database records today?',
        });
    });

    it('should execute query_database_table tool call loop when model requests table data', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { email: 'g.vega.cl@gmail.com' } },
            error: null,
        });

        // Step 1: Model requests query_database_table tool call
        const mockStep1Response = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content: null,
                        tool_calls: [
                            {
                                id: 'call_table_123',
                                type: 'function',
                                function: {
                                    name: 'query_database_table',
                                    arguments: JSON.stringify({
                                        table_name: 'trades',
                                        filter_column: 'ticker',
                                        filter_value: 'NVDA',
                                        limit: 5,
                                    }),
                                },
                            },
                        ],
                    },
                },
            ],
        };

        // Step 2: Model receives tool result and returns final synthesized response
        const mockStep2Response = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content: 'Found 1 recent trade for NVDA in the database.',
                    },
                },
            ],
        };

        (global.fetch as ReturnType<typeof vi.fn>)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => mockStep1Response,
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => mockStep2Response,
            });

        const result = await handleChatMessage({
            messages: [{ role: 'user', content: 'What are the recent NVDA trades?' }],
        });

        expect(global.fetch).toHaveBeenCalledTimes(2);
        expect(result.role).toBe('assistant');
        expect(result.content).toBe('Found 1 recent trade for NVDA in the database.');
        expect(result.tool_traces).toBeDefined();
        expect(result.tool_traces?.[0].tool_name).toBe('query_database_table');
    });

    it('should execute search_memories_and_theses tool call and return tool traces', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { email: 'g.vega.cl@gmail.com' } },
            error: null,
        });

        const mockStep1Response = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content: null,
                        tool_calls: [
                            {
                                id: 'call_mem_123',
                                type: 'function',
                                function: {
                                    name: 'search_memories_and_theses',
                                    arguments: JSON.stringify({
                                        ticker: 'NVO',
                                        limit: 5,
                                    }),
                                },
                            },
                        ],
                    },
                },
            ],
        };

        const mockStep2Response = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content: 'NVO shows solid GLP-1 demand in memory records.',
                    },
                },
            ],
        };

        (global.fetch as ReturnType<typeof vi.fn>)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => mockStep1Response,
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => mockStep2Response,
            });

        const result = await handleChatMessage({
            messages: [{ role: 'user', content: 'Should I invest in NVO?' }],
        });

        expect(global.fetch).toHaveBeenCalledTimes(2);
        expect(result.content).toBe('NVO shows solid GLP-1 demand in memory records.');
        expect(result.tool_traces).toBeDefined();
        expect(result.tool_traces?.[0].tool_name).toBe('search_memories_and_theses');
    });

    it('should execute get_stock_context_and_trades tool call', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { email: 'g.vega.cl@gmail.com' } },
            error: null,
        });

        const mockStep1Response = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content: null,
                        tool_calls: [
                            {
                                id: 'call_stock_123',
                                type: 'function',
                                function: {
                                    name: 'get_stock_context_and_trades',
                                    arguments: JSON.stringify({
                                        ticker: 'AAPL',
                                    }),
                                },
                            },
                        ],
                    },
                },
            ],
        };

        const mockStep2Response = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content: 'Retrieved 2 recent trades for AAPL.',
                    },
                },
            ],
        };

        (global.fetch as ReturnType<typeof vi.fn>)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => mockStep1Response,
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => mockStep2Response,
            });

        const result = await handleChatMessage({
            messages: [{ role: 'user', content: 'Tell me about AAPL trades' }],
        });

        expect(global.fetch).toHaveBeenCalledTimes(2);
        expect(result.content).toBe('Retrieved 2 recent trades for AAPL.');
        expect(result.tool_traces).toBeDefined();
        expect(result.tool_traces?.[0].tool_name).toBe('get_stock_context_and_trades');
    });

    it('should parse suggested_questions from assistant response and strip tags from content', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { email: 'g.vega.cl@gmail.com' } },
            error: null,
        });

        const mockDeepSeekResponse = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content:
                            'Here is the analysis for NVO.\n\n<suggested_questions>\n["Compare NVO win rate against LLY in portfolio trades", "What causal risk factor triggered our last stop-loss?"]\n</suggested_questions>',
                    },
                },
            ],
        };

        (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
            ok: true,
            json: async () => mockDeepSeekResponse,
        });

        const result = await handleChatMessage({
            messages: [{ role: 'user', content: 'Should I invest in NVO?' }],
        });

        expect(result.content).toBe('Here is the analysis for NVO.');
        expect(result.suggested_questions).toEqual([
            'Compare NVO win rate against LLY in portfolio trades',
            'What causal risk factor triggered our last stop-loss?',
        ]);
    });

    it('should handle malformed suggested_questions tag gracefully and sanitize output', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { email: 'g.vega.cl@gmail.com' } },
            error: null,
        });

        const mockDeepSeekResponse = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content:
                            'Analysis complete.<suggested_questions>["Broken JSON without closing',
                    },
                },
            ],
        };

        (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
            ok: true,
            json: async () => mockDeepSeekResponse,
        });

        const result = await handleChatMessage({
            messages: [{ role: 'user', content: 'Tell me about AAPL' }],
        });

        expect(result.content).toBe('Analysis complete.');
        // Should extract any valid quoted strings or fall back safely
        expect(
            Array.isArray(result.suggested_questions) || result.suggested_questions === undefined,
        ).toBe(true);
    });

    it('should report accurate fred_series_cache columns and table-aware default order_by without vectors', async () => {
        const schema = await getDatabaseSchemaSummary(null);
        expect(schema).toContain(
            '- fred_series_cache: series_id, title, units, frequency, latest_date, latest_value, observations, fetched_at',
        );
        expect(schema).not.toContain('fred_series_cache: series_id, fetched_at, data');

        const mockOrder = vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({
                data: [{ series_id: 'FEDFUNDS', latest_value: 4.33, embedding: [0.1, 0.2] }],
                error: null,
            }),
        });
        const mockClient = {
            from: vi.fn().mockReturnValue({
                select: vi.fn().mockReturnValue({
                    eq: vi.fn(),
                    ilike: vi.fn(),
                    contains: vi.fn(),
                    order: mockOrder,
                }),
            }),
        };

        const out = await executeDatabaseQueryTool({ table_name: 'fred_series_cache' }, mockClient);
        expect(mockOrder).toHaveBeenCalledWith('fetched_at', { ascending: false });
        const parsed = JSON.parse(out.result);
        expect(parsed.rows[0].embedding).toBeUndefined();
        expect(parsed.rows[0].series_id).toBe('FEDFUNDS');

        await executeDatabaseQueryTool({ table_name: 'gov_contracts' }, mockClient);
        expect(mockOrder).toHaveBeenLastCalledWith('award_date', { ascending: false });
    });
});
