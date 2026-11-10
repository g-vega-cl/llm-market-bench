const CHUNK_RELOAD_STORAGE_KEY = 'benchify:last_chunk_reload';
const DEFAULT_COOLDOWN_MS = 15000;

/**
 * Checks whether an incoming error corresponds to a dynamic import / chunk load failure.
 * Captures browser-specific signatures from Chromium, WebKit/Safari, Firefox, and Webpack/Rollup.
 */
export function isDynamicChunkError(error: unknown): boolean {
    if (!error) return false;
    const message = (
        error instanceof Error ? error.message : typeof error === 'string' ? error : String(error)
    ).toLowerCase();

    return (
        message.includes('failed to fetch dynamically imported module') ||
        message.includes('error loading dynamically imported module') ||
        message.includes('importing a module script failed') ||
        message.includes('loading chunk')
    );
}

interface TriggerChunkReloadOptions {
    cooldownMs?: number;
    storage?: Storage;
    reloadFn?: () => void;
}

/**
 * Performs a single hard page reload to refresh runtime assets after a deployment.
 * Guarded by a timestamp in sessionStorage to prevent infinite reload loops if an asset
 * is persistently unavailable.
 *
 * @returns true if reload was triggered, false if suppressed by cooldown or SSR.
 */
export function triggerChunkReload(options?: TriggerChunkReloadOptions): boolean {
    if (typeof window === 'undefined') return false;

    const cooldownMs = options?.cooldownMs ?? DEFAULT_COOLDOWN_MS;
    const storage =
        options?.storage ?? (typeof sessionStorage !== 'undefined' ? sessionStorage : null);
    const reloadFn = options?.reloadFn ?? (() => window.location.reload());

    const now = Date.now();

    if (storage) {
        try {
            const lastReload = Number(storage.getItem(CHUNK_RELOAD_STORAGE_KEY) || '0');
            if (now - lastReload < cooldownMs) {
                return false;
            }
            storage.setItem(CHUNK_RELOAD_STORAGE_KEY, String(now));
        } catch {
            // Storage quota or privacy sandbox errors; fall through to execute reload once
        }
    }

    try {
        reloadFn();
        return true;
    } catch {
        return false;
    }
}

interface SetupVitePreloadErrorOptions {
    cooldownMs?: number;
    storage?: Storage;
    reloadFn?: () => void;
}

/**
 * Attaches a global listener for Vite's `vite:preloadError` event.
 * Dispatched automatically by Vite when a dynamically imported chunk fails to fetch.
 */
export function setupVitePreloadErrorHandler(options?: SetupVitePreloadErrorOptions): () => void {
    if (typeof window === 'undefined') {
        return () => {};
    }

    const handler = (event: Event) => {
        event.preventDefault();
        triggerChunkReload(options);
    };

    window.addEventListener('vite:preloadError', handler);

    return () => {
        window.removeEventListener('vite:preloadError', handler);
    };
}
