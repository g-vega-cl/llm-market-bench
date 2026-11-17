import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    claimChunkReloadAttempt,
    isDynamicChunkError,
    reloadAtTarget,
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
        delete (window as unknown as { __benchify_vite_preload_bound__?: boolean })
            .__benchify_vite_preload_bound__;
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

        it('inspects nested error cause for chunk failures', () => {
            const rootErr = new Error('Route transition failed', {
                cause: new TypeError('Failed to fetch dynamically imported module'),
            });
            expect(isDynamicChunkError(rootErr)).toBe(true);
        });

        it('does not over-match unrelated strings containing loading chunk without failed', () => {
            const err = new Error('Finished loading chunk into memory');
            expect(isDynamicChunkError(err)).toBe(false);
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
        it('triggers reload on first invocation and records attempt count and timestamp', () => {
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
                'benchify:chunk_reload_count',
                '1',
            );
            expect(fakeSessionStorage.setItem).toHaveBeenCalledWith(
                'benchify:last_chunk_reload_ts',
                String(now),
            );
        });

        it('suppresses reload on second invocation within cooldown to prevent loops (circuit-breaker)', () => {
            const reloadFn = vi.fn();
            const now = 1000000;
            vi.spyOn(Date, 'now').mockReturnValue(now);

            // First reload
            triggerChunkReload({ storage: fakeSessionStorage, reloadFn });
            expect(reloadFn).toHaveBeenCalledTimes(1);

            // Second reload 10 seconds later (within 60s cooldown window)
            vi.spyOn(Date, 'now').mockReturnValue(now + 10000);
            const secondResult = triggerChunkReload({
                storage: fakeSessionStorage,
                reloadFn,
            });

            expect(secondResult).toBe(false);
            expect(reloadFn).toHaveBeenCalledTimes(1); // Still 1, not called again
        });

        it('resets retry count and allows reload after cooldown window expires', () => {
            const reloadFn = vi.fn();
            const now = 1000000;
            vi.spyOn(Date, 'now').mockReturnValue(now);

            // First reload
            triggerChunkReload({ storage: fakeSessionStorage, reloadFn });
            expect(reloadFn).toHaveBeenCalledTimes(1);

            // Advance 61 seconds (past 60s cooldown)
            vi.spyOn(Date, 'now').mockReturnValue(now + 61000);
            const thirdResult = triggerChunkReload({
                storage: fakeSessionStorage,
                reloadFn,
            });

            expect(thirdResult).toBe(true);
            expect(reloadFn).toHaveBeenCalledTimes(2);
        });

        it('passes targetHref to reloadFn so navigation destination is preserved', () => {
            const reloadFn = vi.fn();
            const target = 'https://www.benchify.dev/portfolios/sys-sentiment-fader';

            triggerChunkReload({
                targetHref: target,
                storage: fakeSessionStorage,
                reloadFn,
            });

            expect(reloadFn).toHaveBeenCalledWith(target);
        });
    });

    describe('claimChunkReloadAttempt and reloadAtTarget', () => {
        it('claimChunkReloadAttempt fails closed on corrupted NaN storage values and resets after cooldown', () => {
            const now = 1000000;
            vi.spyOn(Date, 'now').mockReturnValue(now);

            mockStorage['benchify:chunk_reload_count'] = 'NaN';
            mockStorage['benchify:last_chunk_reload_ts'] = String(now);
            expect(claimChunkReloadAttempt({ storage: fakeSessionStorage })).toBe('circuit_open');

            mockStorage = {};
            expect(claimChunkReloadAttempt({ storage: fakeSessionStorage })).toBe('reloading');
            expect(claimChunkReloadAttempt({ storage: fakeSessionStorage })).toBe('circuit_open');

            vi.spyOn(Date, 'now').mockReturnValue(now + 61000);
            expect(claimChunkReloadAttempt({ storage: fakeSessionStorage })).toBe('reloading');
        });

        it('reloadAtTarget calls location.reload() for relative path with #hash on same page and ignores cross-origin URLs', () => {
            const reloadSpy = vi.fn();
            const originalLocation = window.location;
            const fakeLocation = {
                href: 'https://www.benchify.dev/how-it-works#section',
                origin: 'https://www.benchify.dev',
                pathname: '/how-it-works',
                search: '',
                reload: reloadSpy,
            };
            Object.defineProperty(window, 'location', {
                configurable: true,
                value: fakeLocation,
            });

            try {
                reloadAtTarget('/how-it-works#section');
                expect(reloadSpy).toHaveBeenCalledTimes(1);
                expect(fakeLocation.href).toBe('https://www.benchify.dev/how-it-works#section');

                reloadAtTarget('https://evil.example/phish');
                expect(reloadSpy).toHaveBeenCalledTimes(2);
                expect(fakeLocation.href).toBe('https://www.benchify.dev/how-it-works#section');

                reloadAtTarget('/recipes-demo');
                expect(reloadSpy).toHaveBeenCalledTimes(2);
                expect(fakeLocation.href).toBe('https://www.benchify.dev/recipes-demo');
            } finally {
                Object.defineProperty(window, 'location', {
                    configurable: true,
                    value: originalLocation,
                });
            }
        });

        it('claimChunkReloadAttempt fails closed when sessionStorage throws or getter throws SecurityError', () => {
            const brokenStorage = {
                getItem: vi.fn(() => null),
                setItem: vi.fn(() => {
                    throw new Error('QuotaExceededError');
                }),
            } as unknown as Storage;

            expect(claimChunkReloadAttempt({ storage: brokenStorage })).toBe('circuit_open');

            const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'sessionStorage');
            Object.defineProperty(window, 'sessionStorage', {
                configurable: true,
                get() {
                    throw new DOMException('Blocked', 'SecurityError');
                },
            });
            try {
                expect(claimChunkReloadAttempt()).toBe('circuit_open');
            } finally {
                if (originalDescriptor) {
                    Object.defineProperty(window, 'sessionStorage', originalDescriptor);
                }
            }
        });
    });

    describe('setupVitePreloadErrorHandler', () => {
        it('listens for vite:preloadError and triggers reload', () => {
            const reloadFn = vi.fn();
            const cleanup = setupVitePreloadErrorHandler({
                storage: fakeSessionStorage,
                reloadFn,
            });

            const event = new CustomEvent('vite:preloadError', {
                detail: new Error('Failed to fetch dynamically imported module'),
                cancelable: true,
            });
            window.dispatchEvent(event);

            expect(reloadFn).toHaveBeenCalledTimes(1);
            // Must NOT prevent default, allowing Vite/Router to handle error without resolving undefined
            expect(event.defaultPrevented).toBe(false);

            cleanup();

            const event2 = new CustomEvent('vite:preloadError', { cancelable: true });
            window.dispatchEvent(event2);
            expect(reloadFn).toHaveBeenCalledTimes(1);
        });

        it('is idempotent and prevents duplicate event listeners', () => {
            const reloadFn1 = vi.fn();
            const reloadFn2 = vi.fn();

            const cleanup1 = setupVitePreloadErrorHandler({
                storage: fakeSessionStorage,
                reloadFn: reloadFn1,
            });
            const cleanup2 = setupVitePreloadErrorHandler({
                storage: fakeSessionStorage,
                reloadFn: reloadFn2,
            });

            const event = new CustomEvent('vite:preloadError', { cancelable: true });
            window.dispatchEvent(event);

            expect(reloadFn1).toHaveBeenCalledTimes(1);
            expect(reloadFn2).not.toHaveBeenCalled();

            cleanup1();
            cleanup2();
        });
    });
});
