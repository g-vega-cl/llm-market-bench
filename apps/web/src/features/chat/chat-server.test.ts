import { beforeEach, describe, expect, it, vi } from 'vitest';
import { handleChatMessage } from './chat-server';

// Mock Supabase Server Client
const mockGetUser = vi.fn();
vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: () => ({
        auth: {
            getUser: mockGetUser,
        },
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

    it('should allow g.vega.cl@gmail.com and post to DeepSeek API', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { email: 'g.vega.cl@gmail.com' } },
            error: null,
        });

        const mockDeepSeekResponse = {
            choices: [
                {
                    message: {
                        role: 'assistant',
                        content: 'Hello Cesar! How can I assist you with market data today?',
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

        expect(global.fetch).toHaveBeenCalledWith('https://api.deepseek.com/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: 'Bearer test-deepseek-key',
            },
            body: expect.stringContaining('deepseek-chat'),
        });

        expect(result).toEqual({
            role: 'assistant',
            content: 'Hello Cesar! How can I assist you with market data today?',
        });
    });
});
