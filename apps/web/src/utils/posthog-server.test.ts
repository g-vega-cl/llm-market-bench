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
        vi.resetModules();
    });

    it('returns null without constructing PostHog when no project token is set', async () => {
        vi.stubEnv('VITE_PUBLIC_POSTHOG_PROJECT_TOKEN', '');
        vi.stubEnv('PUBLIC_POSTHOG_PROJECT_TOKEN', '');
        const { getPostHogClient } = await import('./posthog-server');

        expect(getPostHogClient()).toBeNull();
        expect(mockPostHogConstructor).not.toHaveBeenCalled();
        vi.unstubAllEnvs();
    });

    it('initializes and returns a PostHog singleton client when configured', async () => {
        vi.stubEnv('VITE_PUBLIC_POSTHOG_PROJECT_TOKEN', 'phc_server_test');
        const { getPostHogClient } = await import('./posthog-server');
        const client1 = getPostHogClient();
        const client2 = getPostHogClient();

        expect(client1).toBeDefined();
        expect(client1).toBe(client2);
        expect(mockPostHogConstructor).toHaveBeenCalledTimes(1);
        expect(mockPostHogConstructor).toHaveBeenCalledWith(
            'phc_server_test',
            expect.objectContaining({
                flushAt: 1,
                flushInterval: 0,
            }),
        );
        vi.unstubAllEnvs();
    });
});
