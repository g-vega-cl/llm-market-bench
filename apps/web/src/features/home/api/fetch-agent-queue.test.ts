import { beforeEach, describe, expect, it, vi } from 'vitest';

// Module-level mock for Auth and DB clients
let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/auth', () => ({
    getAuthServerClient: vi.fn(() => mockSupabaseClient),
}));
vi.mock('~/lib/db', () => ({
    getDbServerClient: vi.fn(() => mockSupabaseClient),
}));

import {
    handleFetchAgentQueueStatus,
    handleSubmitAgentQueueQuestion,
    validateQueueMessage,
} from './fetch-agent-queue';

describe('validateQueueMessage', () => {
    it('rejects empty or whitespace-only messages', () => {
        expect(() => validateQueueMessage('')).toThrow(/empty/i);
        expect(() => validateQueueMessage('   \n\t  ')).toThrow(/empty/i);
    });

    it('rejects messages longer than 500 characters', () => {
        const longMessage = 'a'.repeat(501);
        expect(() => validateQueueMessage(longMessage)).toThrow(/500 characters/i);
    });

    it('accepts valid messages up to 500 characters and trims them', () => {
        const valid500 = 'x'.repeat(500);
        expect(validateQueueMessage(`  ${valid500}  `)).toBe(valid500);
    });
});

describe('handleSubmitAgentQueueQuestion', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('throws UNAUTHORIZED when no authenticated user is present', async () => {
        mockSupabaseClient = {
            auth: {
                getUser: vi.fn().mockResolvedValue({ data: { user: null }, error: null }),
            },
        };

        await expect(
            handleSubmitAgentQueueQuestion({ message: 'Is SPY bullish?' }),
        ).rejects.toThrow(/UNAUTHORIZED/i);
    });

    it('inserts question with user_id and pending status when authenticated', async () => {
        const mockInsert = vi.fn().mockReturnValue({
            select: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({
                    data: {
                        id: 'q-abc-123',
                        user_id: 'usr-123',
                        display_name: 'alex',
                        message: 'Is SPY bullish?',
                        status: 'pending',
                    },
                    error: null,
                }),
            }),
        });

        mockSupabaseClient = {
            auth: {
                getUser: vi.fn().mockResolvedValue({
                    data: { user: { id: 'usr-123', email: 'alex@example.com' } },
                    error: null,
                }),
            },
            from: vi.fn().mockReturnValue({
                insert: mockInsert,
            }),
        };

        const result = await handleSubmitAgentQueueQuestion({ message: 'Is SPY bullish?' });
        expect(result.success).toBe(true);
        expect(result.item?.id).toBe('q-abc-123');
        expect(mockInsert).toHaveBeenCalledWith(
            expect.objectContaining({
                user_id: 'usr-123',
                display_name: 'alex',
                message: 'Is SPY bullish?',
                status: 'pending',
            }),
        );
    });
});

describe('handleFetchAgentQueueStatus', () => {
    it('returns pendingCount and latestAnswered item', async () => {
        const mockEq = vi.fn().mockResolvedValue({ count: 4, error: null });
        const mockSelectPending = vi.fn().mockReturnValue({ eq: mockEq });

        const mockLimit = vi.fn().mockResolvedValue({
            data: [
                {
                    id: 'q-ans-1',
                    message: 'Will SPY break $580?',
                    agent_response: 'SPY held $580 support on strong volume.',
                    display_name: 'bob',
                },
            ],
            error: null,
        });
        const mockOrder = vi.fn().mockReturnValue({ limit: mockLimit });
        const mockNot = vi.fn().mockReturnValue({ order: mockOrder });
        const mockSelectAnswered = vi.fn().mockReturnValue({ not: mockNot });

        mockSupabaseClient = {
            from: vi.fn().mockImplementation((table: string) => {
                if (table === 'agent_chat_queue') {
                    return {
                        select: vi
                            .fn()
                            .mockImplementation((_cols: string, opts?: { count?: string }) => {
                                if (opts?.count === 'exact') {
                                    return mockSelectPending();
                                }
                                return mockSelectAnswered();
                            }),
                    };
                }
                return {};
            }),
        };

        const status = await handleFetchAgentQueueStatus();
        expect(status.pendingCount).toBe(4);
        expect(status.latestAnswered?.id).toBe('q-ans-1');
        expect(status.latestAnswered?.agent_response).toBe(
            'SPY held $580 support on strong volume.',
        );
    });
});
