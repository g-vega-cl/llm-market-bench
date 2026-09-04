import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    handleDistillChatMemory,
    handleFetchMyChatMemories,
    handleSaveChatMemory,
} from './chat-server';
import { executeGetMySavedThesesTool } from './chat-tools';

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

describe('Chat Memories Server Handlers', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        vi.clearAllMocks();
        global.fetch = vi.fn();
        process.env = { ...originalEnv, DEEPSEEK_API_KEY: 'test-deepseek-key' };
    });

    describe('handleDistillChatMemory', () => {
        it('should reject unauthenticated requests', async () => {
            mockGetUser.mockResolvedValue({ data: { user: null }, error: null });

            await expect(
                handleDistillChatMemory({
                    userQuery: 'Should I invest in NVO?',
                    assistantResponse: 'NVO has strong GLP-1 revenue growth...',
                }),
            ).rejects.toThrow('Authentication required');
        });

        it('should reject unauthorized user emails', async () => {
            mockGetUser.mockResolvedValue({
                data: { user: { id: 'u1', email: 'intruder@example.com' } },
                error: null,
            });

            await expect(
                handleDistillChatMemory({
                    userQuery: 'Should I invest in NVO?',
                    assistantResponse: 'NVO has strong GLP-1 revenue growth...',
                }),
            ).rejects.toThrow('Chat feature is restricted to authorized accounts');
        });

        it('should call DeepSeek API with distillation prompt and return structured thesis', async () => {
            mockGetUser.mockResolvedValue({
                data: { user: { id: 'u1', email: 'g.vega.cl@gmail.com' } },
                error: null,
            });

            const mockDistilledPayload = {
                ticker: 'NVO',
                thesis: 'NVO revenue growth in obesity remains solid, but margin expansion is stalling due to manufacturing capex and intense LLY competition.',
                tags: ['GLP-1', 'margin-compression', 'pharma'],
                importance_score: 8,
            };

            (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
                ok: true,
                json: async () => ({
                    choices: [
                        {
                            message: {
                                role: 'assistant',
                                content: `\`\`\`json\n${JSON.stringify(mockDistilledPayload)}\n\`\`\``,
                            },
                        },
                    ],
                }),
            });

            const result = await handleDistillChatMemory({
                userQuery: 'Should I invest in NVO based on current memories and trades?',
                assistantResponse:
                    'NVO shows strong GLP-1 revenue growth, but recent agent trades trimmed exposure due to margin normalization.',
            });

            expect(global.fetch).toHaveBeenCalledTimes(1);
            expect(result).toEqual(mockDistilledPayload);
        });

        it('should include custom instructions when provided', async () => {
            mockGetUser.mockResolvedValue({
                data: { user: { id: 'u1', email: 'g.vega.cl@gmail.com' } },
                error: null,
            });

            (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
                ok: true,
                json: async () => ({
                    choices: [
                        {
                            message: {
                                role: 'assistant',
                                content: JSON.stringify({
                                    ticker: 'NVO',
                                    thesis: 'Supply bottlenecks for Wegovy will cap near-term market share gains.',
                                    tags: ['supply-chain', 'pharma'],
                                    importance_score: 9,
                                }),
                            },
                        },
                    ],
                }),
            });

            await handleDistillChatMemory({
                userQuery: 'Tell me about NVO supply issues',
                assistantResponse: 'Production has faced delays...',
                customInstruction: 'Focus strictly on the manufacturing bottlenecks and timeline',
            });

            const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
            const body = JSON.parse(fetchCall[1].body);
            expect(body.messages[1].content).toContain(
                'Focus strictly on the manufacturing bottlenecks and timeline',
            );
        });
    });

    describe('handleSaveChatMemory', () => {
        it('should reject unauthenticated requests', async () => {
            mockGetUser.mockResolvedValue({ data: { user: null }, error: null });

            await expect(
                handleSaveChatMemory({
                    ticker: 'NVO',
                    thesis: 'A distilled thesis',
                }),
            ).rejects.toThrow('Authentication required');
        });

        it('should insert record into chat_memories with user_id', async () => {
            mockGetUser.mockResolvedValue({
                data: { user: { id: 'user-123-abc', email: 'g.vega.cl@gmail.com' } },
                error: null,
            });

            const insertedRow = {
                id: 'mem-999',
                user_id: 'user-123-abc',
                ticker: 'NVO',
                thesis: 'NVO margin pressure thesis',
                tags: ['GLP-1'],
                importance_score: 8,
                source_query: 'Should I invest in NVO?',
                created_at: '2026-09-04T12:00:00Z',
            };

            const mockInsert = vi.fn().mockReturnValue({
                select: vi.fn().mockReturnValue({
                    single: vi.fn().mockResolvedValue({ data: insertedRow, error: null }),
                }),
            });

            mockFrom.mockReturnValue({
                insert: mockInsert,
            });

            const result = await handleSaveChatMemory({
                ticker: 'NVO',
                thesis: 'NVO margin pressure thesis',
                tags: ['GLP-1'],
                importance_score: 8,
                sourceQuery: 'Should I invest in NVO?',
            });

            expect(mockFrom).toHaveBeenCalledWith('chat_memories');
            expect(mockInsert).toHaveBeenCalledWith({
                user_id: 'user-123-abc',
                ticker: 'NVO',
                thesis: 'NVO margin pressure thesis',
                tags: ['GLP-1'],
                importance_score: 8,
                source_query: 'Should I invest in NVO?',
            });
            expect(result).toEqual(insertedRow);
        });

        it('should validate that thesis is provided and non-empty', async () => {
            mockGetUser.mockResolvedValue({
                data: { user: { id: 'user-123-abc', email: 'g.vega.cl@gmail.com' } },
                error: null,
            });

            await expect(
                handleSaveChatMemory({
                    ticker: 'NVO',
                    thesis: '   ',
                }),
            ).rejects.toThrow('Thesis content is required');
        });
    });

    describe('handleFetchMyChatMemories', () => {
        it('should fetch chat memories for the authenticated user only', async () => {
            mockGetUser.mockResolvedValue({
                data: { user: { id: 'user-123-abc', email: 'g.vega.cl@gmail.com' } },
                error: null,
            });

            const sampleRows = [
                {
                    id: 'mem-1',
                    user_id: 'user-123-abc',
                    ticker: 'NVO',
                    thesis: 'Thesis on NVO',
                    tags: ['pharma'],
                    importance_score: 8,
                    created_at: '2026-09-04T12:00:00Z',
                },
            ];

            const mockOrder = vi.fn().mockResolvedValue({ data: sampleRows, error: null });
            const mockEqUser = vi.fn().mockReturnValue({ order: mockOrder });
            const mockSelect = vi.fn().mockReturnValue({ eq: mockEqUser });

            mockFrom.mockReturnValue({
                select: mockSelect,
            });

            const result = await handleFetchMyChatMemories({});

            expect(mockFrom).toHaveBeenCalledWith('chat_memories');
            expect(mockEqUser).toHaveBeenCalledWith('user_id', 'user-123-abc');
            expect(result).toEqual(sampleRows);
        });
    });

    describe('executeGetMySavedThesesTool', () => {
        it('should retrieve user saved theses matching ticker from chat_memories', async () => {
            const mockSelect = vi.fn();
            const mockEqUser = vi.fn();
            const mockEqTicker = vi.fn();
            const mockOrder = vi.fn();

            const mockLimit = vi.fn().mockResolvedValue({
                data: [
                    {
                        id: 'mem-1',
                        ticker: 'NVO',
                        thesis: 'NVO capex margin drag',
                        tags: ['pharma'],
                        importance_score: 8,
                        created_at: '2026-09-04T12:00:00Z',
                    },
                ],
                error: null,
            });

            mockOrder.mockReturnValue({ limit: mockLimit });
            mockEqTicker.mockReturnValue({ order: mockOrder });
            mockEqUser.mockReturnValue({
                eq: mockEqTicker,
                order: mockOrder,
            });
            mockSelect.mockReturnValue({ eq: mockEqUser });

            const mockSupabase = {
                from: vi.fn().mockReturnValue({ select: mockSelect }),
            };

            const { result, trace } = await executeGetMySavedThesesTool(
                { ticker: 'NVO' },
                mockSupabase,
                'user-123-abc',
            );

            expect(mockSupabase.from).toHaveBeenCalledWith('chat_memories');
            expect(mockEqUser).toHaveBeenCalledWith('user_id', 'user-123-abc');
            expect(mockEqTicker).toHaveBeenCalledWith('ticker', 'NVO');
            expect(trace.tool_name).toBe('get_my_saved_theses');
            expect(trace.summary).toContain('Retrieved 1 saved thesis for NVO');
            expect(result).toContain('NVO capex margin drag');
        });
    });
});
