import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockPostHogConstructor = vi.fn();

vi.mock('posthog-node', () => {
    return {
        PostHog: class MockPostHog {
            options: unknown;
            apiKey: string;
            constructor(apiKey: string, options: unknown) {
                this.apiKey = apiKey;
                this.options = options;
                mockPostHogConstructor(apiKey, options);
            }
        },
    };
});

describe('posthog-server getPostHogClient', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('initializes and returns a PostHog singleton client', async () => {
        const { getPostHogClient } = await import('./posthog-server');
        const client1 = getPostHogClient();
        const client2 = getPostHogClient();

        expect(client1).toBeDefined();
        expect(client1).toBe(client2);
        expect(mockPostHogConstructor).toHaveBeenCalledTimes(1);
        expect(mockPostHogConstructor).toHaveBeenCalledWith(
            expect.any(String),
            expect.objectContaining({
                flushAt: 1,
                flushInterval: 0,
            }),
        );
    });
});
