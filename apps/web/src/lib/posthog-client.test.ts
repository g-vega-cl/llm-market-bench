import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const initMock = vi.fn();
const captureMock = vi.fn();
const identifyMock = vi.fn();
const resetMock = vi.fn();

const mockPostHog = {
    init: initMock,
    capture: captureMock,
    identify: identifyMock,
    reset: resetMock,
};

vi.mock('posthog-js', () => ({
    default: mockPostHog,
}));

describe('posthog-client init config (lazy)', () => {
    beforeEach(() => {
        initMock.mockReset();
        captureMock.mockReset();
        identifyMock.mockReset();
        resetMock.mockReset();
        vi.resetModules();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('does NOT call posthog.init() at module import time', async () => {
        await import('./posthog-client');
        expect(initMock).not.toHaveBeenCalled();
    });

    it('disables PostHog exception-autocapture to avoid loading extra /static JS', async () => {
        const mod = await import('./posthog-client');
        await mod.initPostHog();
        expect(initMock).toHaveBeenCalledTimes(1);
        const config = initMock.mock.calls[0][1];
        expect(config.capture_exceptions).toBe(false);
        expect(config.capture_dead_clicks).toBe(false);
    });

    it('uses the stealthy reverse proxy /p api_host for browser environments', async () => {
        const mod = await import('./posthog-client');
        await mod.initPostHog();
        const config = initMock.mock.calls[0][1];
        expect(config.api_host).toBe('/p');
    });

    it('disables surveys to reduce unused JS payload', async () => {
        const mod = await import('./posthog-client');
        await mod.initPostHog();
        const config = initMock.mock.calls[0][1];
        expect(config.disable_surveys).toBe(true);
    });

    it('is idempotent: calling initPostHog() twice still triggers init once', async () => {
        const mod = await import('./posthog-client');
        await mod.initPostHog();
        await mod.initPostHog();
        expect(initMock).toHaveBeenCalledTimes(1);
    });
});
