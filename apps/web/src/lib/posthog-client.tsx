/**
 * Lazy PostHog client.
 *
 * Why this exists
 * ---------------
 * The previous implementation rendered `<PostHogProvider>` synchronously from the
 * root layout, which caused PostHog's `posthog-js` runtime to be parsed and
 * executed on the critical path. That pulls ~30 KiB of JS into the initial bundle
 * and (because of `capture_exceptions: true` and the default autocapture
 * settings) triggers the browser to fetch `exception-autocapture.js` and
 * `dead-clicks-autocapture.js` from PostHog's CDN, blocking LCP and increasing
 * LCP by ~400 ms in our Lighthouse run.
 *
 * Critically, `@posthog/react` has a STATIC import of `posthog-js`, so any
 * `import { usePostHog } from '@posthog/react'` pulls `posthog-js` into the
 * main bundle. We avoid that by:
 *   1. Re-implementing `PostHogProvider` ourselves (a thin React context wrapper
 *      around the lazily-imported posthog-js instance).
 *   2. Exposing `useAnalytics()` — a custom hook that reads from our context.
 *   3. Keeping all `posthog-js` code paths behind `await import('posthog-js')`.
 *
 * This module MUST NOT call `posthog.init()` at import time.
 */

import type * as React from 'react';
import { createContext, useContext, useEffect, useState } from 'react';

export type PostHogLike = {
    init: (key: string, config: Record<string, unknown>) => void;
    capture: (event: string, props?: Record<string, unknown>) => void;
    identify: (distinctId: string, props?: Record<string, unknown>) => void;
    reset: () => void;
};

let posthogInstance: PostHogLike | null = null;
let initStarted = false;
let initPromise: Promise<PostHogLike | null> | null = null;

const NOOP_ANALYTICS: PostHogLike = {
    init: () => {},
    capture: () => {},
    identify: () => {},
    reset: () => {},
};

const PostHogContext = createContext<PostHogLike | null>(null);

/**
 * Centralized init config. Tests assert against this to keep config in sync.
 */
export function getPostHogInitConfig(): {
    apiKey: string;
    config: Record<string, unknown>;
} {
    return {
        apiKey: import.meta.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN || '',
        config: {
            api_host: typeof window !== 'undefined' ? '/p' : 'https://us.i.posthog.com',
            ui_host: 'https://us.posthog.com',
            defaults: '2025-05-24',
            // Autocapture disabled → no extra /static JS requests on init
            capture_exceptions: false,
            capture_dead_clicks: false,
            disable_session_recording: true,
            disable_surveys: true,
        },
    };
}

/**
 * Lazily import posthog-js and init it. Idempotent; safe to call multiple times.
 */
export async function initPostHog(): Promise<PostHogLike | null> {
    if (typeof window === 'undefined') return null;
    if (posthogInstance) return posthogInstance;
    if (initPromise) return initPromise;

    initPromise = (async () => {
        initStarted = true;
        const mod = await import('posthog-js');
        const posthog = mod.default as unknown as PostHogLike;
        const { apiKey, config } = getPostHogInitConfig();
        if (apiKey) {
            posthog.init(apiKey, config);
        }
        posthogInstance = posthog;
        return posthog;
    })();

    return initPromise;
}

/**
 * Returns true once initPostHog() has been called at least once.
 * Used by useAnalytics to know whether to short-circuit to the real client.
 */
export function isPostHogInitialized(): boolean {
    return initStarted;
}

function getPostHogClient(): PostHogLike | null {
    return posthogInstance;
}

interface PostHogLazyBoundaryProps {
    children: React.ReactNode;
}

/**
 * Renders children inside a custom PostHog context provider. The provider's
 * value is set only after PostHog's lazy init resolves, so the posthog-js
 * runtime is NOT on the critical render path.
 */
export function PostHogLazyBoundary({ children }: PostHogLazyBoundaryProps) {
    const [client, setClient] = useState<PostHogLike | null>(getPostHogClient());

    useEffect(() => {
        if (initStarted) {
            if (posthogInstance) setClient(posthogInstance);
            return;
        }

        type WindowWithIdle = Window & {
            requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number;
            cancelIdleCallback?: (id: number) => void;
        };
        const w = window as WindowWithIdle;
        const schedule = w.requestIdleCallback
            ? (cb: () => void) => w.requestIdleCallback?.(cb, { timeout: 2000 })
            : (cb: () => void) => setTimeout(cb, 2000);

        const handle = schedule(() => {
            initPostHog().then((instance) => {
                if (instance) setClient(instance);
            });
        });

        return () => {
            if (typeof handle === 'number') {
                if (w.cancelIdleCallback) w.cancelIdleCallback(handle);
                else clearTimeout(handle);
            }
        };
    }, []);

    return <PostHogContext.Provider value={client}>{children}</PostHogContext.Provider>;
}

/**
 * Drop-in replacement for `usePostHog()` that returns a noop until PostHog
 * is initialized. Components that call `.capture()` are always safe to render
 * during the first ~2 s of page life.
 */
export function useAnalytics(): PostHogLike {
    const ctx = useContext(PostHogContext);
    if (initStarted && ctx) {
        return ctx;
    }
    return NOOP_ANALYTICS;
}
