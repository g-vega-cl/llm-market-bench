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

function readReloadState(
    storage: Storage | null,
    cooldownMs: number,
    now: number,
): { count: number } {
    if (!storage) return { count: Number.POSITIVE_INFINITY };
    const rawTs = storage.getItem(CHUNK_RELOAD_TS_KEY);
    const rawCount = storage.getItem(CHUNK_RELOAD_COUNT_KEY);
    const lastTs = rawTs === null || rawTs === '' ? 0 : Number(rawTs);
    let count = rawCount === null || rawCount === '' ? 0 : Number(rawCount);
    if (!Number.isFinite(lastTs) || !Number.isFinite(count) || lastTs < 0 || count < 0) {
        // Fail closed if storage values are corrupted so reloads can never loop infinitely
        return { count: Number.POSITIVE_INFINITY };
    }
    // Reset counter if previous attempt happened outside the cooldown window
    if (now - lastTs > cooldownMs) {
        count = 0;
    }
    return { count };
}

/**
 * Hard-reloads the current document or navigates to a different same-origin route URL.
 * Resolves relative URLs against `window.location.href` and compares origin+pathname+search
 * so same-document `#hash` URLs trigger a real `location.reload()` rather than a hash jump.
 */
export function reloadAtTarget(url?: string): void {
    if (typeof window === 'undefined') return;

    if (!url) {
        window.location.reload();
        return;
    }

    try {
        const currentUrl = new URL(window.location.href);
        const targetUrl = new URL(url, window.location.href);
        if (targetUrl.origin !== currentUrl.origin) {
            window.location.reload();
            return;
        }
        if (targetUrl.pathname === currentUrl.pathname && targetUrl.search === currentUrl.search) {
            window.location.reload();
        } else {
            window.location.href = targetUrl.href;
        }
    } catch {
        window.location.reload();
    }
}

function shouldAllowReloadAttempt(
    storage: Storage | null,
    cooldownMs: number,
    maxRetries: number,
    now: number,
): boolean {
    if (!storage) return false;

    try {
        const { count } = readReloadState(storage, cooldownMs, now);

        // Hard circuit-breaker: fail closed if max retries exceeded
        if (count >= maxRetries) {
            return false;
        }

        storage.setItem(CHUNK_RELOAD_COUNT_KEY, String(count + 1));
        storage.setItem(CHUNK_RELOAD_TS_KEY, String(now));
        return true;
    } catch {
        // Fail closed when storage is blocked/full so reloads can never loop infinitely
        return false;
    }
}

function getSessionStorageSafe(provided?: Storage): Storage | null {
    if (provided !== undefined) {
        return provided;
    }
    try {
        return typeof sessionStorage !== 'undefined' ? sessionStorage : null;
    } catch {
        return null;
    }
}

export type ChunkReloadClaimStatus = 'reloading' | 'circuit_open';

/**
 * Atomically claims a single chunk-reload slot in sessionStorage before dispatching navigation.
 * Guarantees telemetry sees the authoritative reload decision before teardown starts.
 */
export function claimChunkReloadAttempt(
    options?: Pick<TriggerChunkReloadOptions, 'cooldownMs' | 'maxRetries' | 'storage'>,
): ChunkReloadClaimStatus {
    if (typeof window === 'undefined') return 'circuit_open';

    const cooldownMs = options?.cooldownMs ?? DEFAULT_COOLDOWN_WINDOW_MS;
    const maxRetries = options?.maxRetries ?? MAX_AUTO_RELOADS;
    const storage = getSessionStorageSafe(options?.storage);

    return shouldAllowReloadAttempt(storage, cooldownMs, maxRetries, Date.now())
        ? 'reloading'
        : 'circuit_open';
}

/**
 * Performs a single hard page reload or redirect to refresh runtime assets after a deployment.
 * Guarded by an attempt counter circuit-breaker in sessionStorage to eliminate infinite reload loops.
 *
 * @returns true if reload was triggered, false if suppressed by circuit-breaker or SSR.
 */
export function triggerChunkReload(options?: TriggerChunkReloadOptions): boolean {
    if (typeof window === 'undefined') return false;
    if (claimChunkReloadAttempt(options) !== 'reloading') {
        return false;
    }

    const reloadFn = options?.reloadFn ?? reloadAtTarget;
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
