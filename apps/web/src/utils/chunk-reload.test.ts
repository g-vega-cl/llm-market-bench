import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    isDynamicChunkError,
    setupVitePreloadErrorHandler,
    triggerChunkReload,
} from './chunk-reload';

describe('chunk-reload utilities', () => {
    let mockStorage: Record<string, string> = {};
    const fakeSessionStorage = {
        getItem: vi.fn((key: string) => mockStorage[key] ?? null),
        setItem: vi.fn((key: string, value: string) => {
            mockStorage[key] = value;
        }),
        removeItem: vi.fn((key: string) => {
            delete mockStorage[key];
        }),
        clear: vi.fn(() => {
            mockStorage = {};
        }),
    } as unknown as Storage;

    beforeEach(() => {
        mockStorage = {};
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('isDynamicChunkError', () => {
        it('identifies Chrome/Brave dynamic import failure', () => {
            const err = new TypeError(
                'Failed to fetch dynamically imported module: https://www.benchify.dev/assets/index-CZJZmMUs.js',
            );
            expect(isDynamicChunkError(err)).toBe(true);
        });

        it('identifies Safari/WebKit module script failure', () => {
            const err = new TypeError('Importing a module script failed.');
            expect(isDynamicChunkError(err)).toBe(true);
        });

        it('identifies Firefox dynamic import failure', () => {
            const err = new TypeError('error loading dynamically imported module');
            expect(isDynamicChunkError(err)).toBe(true);
        });

        it('identifies Webpack/Rollup chunk load failure', () => {
            const err = new Error('Loading chunk 42 failed.');
            expect(isDynamicChunkError(err)).toBe(true);
        });

        it('handles string errors directly', () => {
            expect(
                isDynamicChunkError(
                    'Failed to fetch dynamically imported module: https://example.com/asset.js',
                ),
            ).toBe(true);
        });

        it('returns false for unrelated errors', () => {
            expect(isDynamicChunkError(new Error('Network timeout'))).toBe(false);
            expect(isDynamicChunkError(new TypeError('Cannot read property of undefined'))).toBe(
                false,
            );
            expect(isDynamicChunkError(null)).toBe(false);
            expect(isDynamicChunkError(undefined)).toBe(false);
        });
    });

    describe('triggerChunkReload', () => {
        it('triggers reload on first invocation and records timestamp', () => {
            const reloadFn = vi.fn();
            const now = 1000000;
            vi.spyOn(Date, 'now').mockReturnValue(now);

            const result = triggerChunkReload({
                storage: fakeSessionStorage,
                reloadFn,
            });

            expect(result).toBe(true);
            expect(reloadFn).toHaveBeenCalledTimes(1);
            expect(fakeSessionStorage.setItem).toHaveBeenCalledWith(
                'benchify:last_chunk_reload',
                String(now),
            );
        });

        it('suppresses reload within cooldown window to prevent reload loops', () => {
            const reloadFn = vi.fn();
            const now = 1000000;
            vi.spyOn(Date, 'now').mockReturnValue(now);

            // First reload
            triggerChunkReload({ storage: fakeSessionStorage, reloadFn });
            expect(reloadFn).toHaveBeenCalledTimes(1);

            // Second reload 5 seconds later (within 15s cooldown)
            vi.spyOn(Date, 'now').mockReturnValue(now + 5000);
            const secondResult = triggerChunkReload({
                storage: fakeSessionStorage,
                reloadFn,
            });

            expect(secondResult).toBe(false);
            expect(reloadFn).toHaveBeenCalledTimes(1); // Still 1, not called again
        });

        it('allows reload after cooldown window expires', () => {
            const reloadFn = vi.fn();
            const now = 1000000;
            vi.spyOn(Date, 'now').mockReturnValue(now);

            // First reload
            triggerChunkReload({ storage: fakeSessionStorage, reloadFn });
            expect(reloadFn).toHaveBeenCalledTimes(1);

            // Advance 16 seconds (past 15s cooldown)
            vi.spyOn(Date, 'now').mockReturnValue(now + 16000);
            const thirdResult = triggerChunkReload({
                storage: fakeSessionStorage,
                reloadFn,
            });

            expect(thirdResult).toBe(true);
            expect(reloadFn).toHaveBeenCalledTimes(2);
        });
    });

    describe('setupVitePreloadErrorHandler', () => {
        it('listens for vite:preloadError and triggers reload', () => {
            const reloadFn = vi.fn();
            const cleanup = setupVitePreloadErrorHandler({
                storage: fakeSessionStorage,
                reloadFn,
            });

            // Dispatch synthetic vite:preloadError event
            const event = new CustomEvent('vite:preloadError', {
                detail: new Error('Failed to fetch dynamically imported module'),
                cancelable: true,
            });
            window.dispatchEvent(event);

            expect(reloadFn).toHaveBeenCalledTimes(1);
            expect(event.defaultPrevented).toBe(true);

            cleanup();

            // Dispatching after cleanup should not invoke reloadFn again
            const event2 = new CustomEvent('vite:preloadError', { cancelable: true });
            window.dispatchEvent(event2);
            expect(reloadFn).toHaveBeenCalledTimes(1);
        });
    });
});
