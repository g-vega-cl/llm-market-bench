import { useEffect, useRef } from 'react';

export interface UseWindowFocusRefreshOptions {
    /**
     * Callback invoked to refresh data when window gains focus or document becomes visible.
     */
    onRefresh: () => void;
    /**
     * Minimum interval in milliseconds between refreshes to avoid spamming the server.
     * Default: 5000ms.
     */
    throttleMs?: number;
    /**
     * Optional PostHog client to synchronize feature flags and capture telemetry.
     */
    posthog?: {
        reloadFeatureFlags?: () => void;
        capture?: (event: string, properties?: Record<string, unknown>) => void;
    } | null;
    /**
     * Whether focus refresh is enabled (default: true).
     */
    enabled?: boolean;
}

export function useWindowFocusRefresh({
    onRefresh,
    throttleMs = 5000,
    posthog,
    enabled = true,
}: UseWindowFocusRefreshOptions) {
    const lastRefreshRef = useRef<number>(Date.now());
    const onRefreshRef = useRef(onRefresh);
    onRefreshRef.current = onRefresh;

    useEffect(() => {
        if (!enabled || typeof window === 'undefined') return;

        const handleFocusOrVisible = () => {
            if (typeof document !== 'undefined' && document.hidden) return;

            const now = Date.now();
            if (now - lastRefreshRef.current < throttleMs) return;
            lastRefreshRef.current = now;

            onRefreshRef.current();

            if (posthog) {
                posthog.reloadFeatureFlags?.();
                posthog.capture?.('window_focus_refreshed', { path: '/' });
            }
        };

        window.addEventListener('focus', handleFocusOrVisible);
        document.addEventListener('visibilitychange', handleFocusOrVisible);

        return () => {
            window.removeEventListener('focus', handleFocusOrVisible);
            document.removeEventListener('visibilitychange', handleFocusOrVisible);
        };
    }, [enabled, throttleMs, posthog]);
}
