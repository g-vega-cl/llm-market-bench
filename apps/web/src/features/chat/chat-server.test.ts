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
        expect(body.tools[0].function.name).toBe('query_database_table');

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
        expect(result).toEqual({
            role: 'assistant',
            content: 'Found 1 recent trade for NVDA in the database.',
        });
    });
});
