import { beforeEach, describe, expect, it, vi } from 'vitest';
import { handleChatMessage } from './chat-server';

// Mock Supabase Server Client
const mockGetUser = vi.fn();
const mockFrom = vi.fn();
vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: () => ({
        auth: {
            getUser: mockGetUser,
        },
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

        // Verify system prompt includes database table catalog
        expect(body.messages[0].role).toBe('system');
        expect(body.messages[0].content).toContain('Available Database Tables:');

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
});
