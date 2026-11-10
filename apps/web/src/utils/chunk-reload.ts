const CHUNK_RELOAD_COUNT_KEY = 'benchify:chunk_reload_count';
const CHUNK_RELOAD_TS_KEY = 'benchify:last_chunk_reload_ts';
const DEFAULT_COOLDOWN_WINDOW_MS = 60000;
const MAX_AUTO_RELOADS = 1;

declare global {
    interface Window {
        __benchify_vite_preload_bound__?: boolean;
    }
}

/**
 * Checks whether an incoming error corresponds to a dynamic import / chunk load failure.
 * Inspects both error message and nested error cause across Chromium, Safari, Firefox, and Webpack/Rollup.
 */
export function isDynamicChunkError(error: unknown): boolean {
    if (!error) return false;

    const extract = (err: unknown): string => {
        if (!err) return '';
        if (err instanceof Error) {
            const causeMsg =
                err.cause instanceof Error
                    ? err.cause.message
                    : typeof err.cause === 'string'
                      ? err.cause
                      : '';
            return `${err.message} ${causeMsg}`;
        }
        return typeof err === 'string' ? err : String(err);
    };

    const message = extract(error).toLowerCase();

    return (
        message.includes('failed to fetch dynamically imported module') ||
        message.includes('error loading dynamically imported module') ||
        message.includes('importing a module script failed') ||
        (message.includes('loading chunk') && message.includes('failed'))
    );
}

interface TriggerChunkReloadOptions {
    targetHref?: string;
    cooldownMs?: number;
    maxRetries?: number;
    storage?: Storage;
    reloadFn?: (url?: string) => void;
}

function shouldAllowReloadAttempt(
    storage: Storage | null,
    cooldownMs: number,
    maxRetries: number,
    now: number,
): boolean {
    if (!storage) return true;

    try {
        const lastTs = Number(storage.getItem(CHUNK_RELOAD_TS_KEY) || '0');
        let count = Number(storage.getItem(CHUNK_RELOAD_COUNT_KEY) || '0');

        // Reset counter if previous attempt happened outside the cooldown window
        if (now - lastTs > cooldownMs) {
            count = 0;
        }

        // Hard circuit-breaker: fail closed if max retries exceeded
        if (count >= maxRetries) {
            return false;
        }

        storage.setItem(CHUNK_RELOAD_COUNT_KEY, String(count + 1));
        storage.setItem(CHUNK_RELOAD_TS_KEY, String(now));
        return true;
    } catch {
        // Storage quota or privacy sandbox errors; fall through to allow reload once
        return true;
    }
}

/**
 * Performs a single hard page reload or redirect to refresh runtime assets after a deployment.
 * Guarded by an attempt counter circuit-breaker in sessionStorage to eliminate infinite reload loops.
 *
 * @returns true if reload was triggered, false if suppressed by circuit-breaker or SSR.
 */
export function triggerChunkReload(options?: TriggerChunkReloadOptions): boolean {
    if (typeof window === 'undefined') return false;

    const cooldownMs = options?.cooldownMs ?? DEFAULT_COOLDOWN_WINDOW_MS;
    const maxRetries = options?.maxRetries ?? MAX_AUTO_RELOADS;
    const storage =
        options?.storage ?? (typeof sessionStorage !== 'undefined' ? sessionStorage : null);
    const reloadFn =
        options?.reloadFn ??
        ((url?: string) => {
            if (url && typeof window !== 'undefined' && url !== window.location.href) {
                window.location.href = url;
            } else if (typeof window !== 'undefined') {
                window.location.reload();
            }
        });

    const now = Date.now();
    if (!shouldAllowReloadAttempt(storage, cooldownMs, maxRetries, now)) {
        return false;
    }

    try {
        reloadFn(options?.targetHref);
        return true;
    } catch {
        return false;
    }
}

interface SetupVitePreloadErrorOptions {
    storage?: Storage;
    reloadFn?: (url?: string) => void;
}

/**
 * Attaches an idempotent global listener for Vite's `vite:preloadError` event.
 * Dispatched automatically by Vite when a dynamically imported chunk fails to fetch.
 */
export function setupVitePreloadErrorHandler(options?: SetupVitePreloadErrorOptions): () => void {
    if (typeof window === 'undefined') {
        return () => {};
    }

    if (window.__benchify_vite_preload_bound__) {
        return () => {};
    }
    window.__benchify_vite_preload_bound__ = true;

    const handler = (_event: Event) => {
        // Do NOT call event.preventDefault()!
        // Calling event.preventDefault() suppresses Vite's error throwing and resolves the dynamic import
        // promise to undefined, causing TanStack Router's lazyRouteComponent to crash with
        // TypeError: Cannot read properties of undefined (reading 'component').
        triggerChunkReload(options);
    };

    window.addEventListener('vite:preloadError', handler);

    return () => {
        window.__benchify_vite_preload_bound__ = false;
        window.removeEventListener('vite:preloadError', handler);
    };
}
