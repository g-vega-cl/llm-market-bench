import { useEffect, useRef } from 'react';

const TURNSTILE_SCRIPT_SRC =
    'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';

interface TurnstileApi {
    render: (
        container: HTMLElement,
        options: {
            sitekey: string;
            theme?: 'light' | 'dark' | 'auto';
            callback?: (token: string) => void;
            'expired-callback'?: () => void;
            'error-callback'?: () => void;
        },
    ) => string;
    reset: (widgetId?: string) => void;
    remove: (widgetId: string) => void;
}

declare global {
    interface Window {
        turnstile?: TurnstileApi;
    }
}

export interface TurnstileWidgetProps {
    siteKey?: string;
    resetKey?: number;
    onToken: (token: string | null) => void;
}

function loadTurnstileScript(onReady: () => void): () => void {
    if (window.turnstile) {
        onReady();
        return () => {};
    }

    const existing = document.querySelector<HTMLScriptElement>(
        `script[src="${TURNSTILE_SCRIPT_SRC}"]`,
    );
    if (existing) {
        existing.addEventListener('load', onReady);
        return () => existing.removeEventListener('load', onReady);
    }

    const script = document.createElement('script');
    script.src = TURNSTILE_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.addEventListener('load', onReady);
    document.head.appendChild(script);
    return () => script.removeEventListener('load', onReady);
}

/**
 * Renders Cloudflare Turnstile when `VITE_TURNSTILE_SITE_KEY` is configured.
 * No-ops cleanly when unset so local environments without Turnstile keep working.
 */
export function TurnstileWidget({
    siteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY,
    resetKey = 0,
    onToken,
}: TurnstileWidgetProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const widgetIdRef = useRef<string | null>(null);
    const onTokenRef = useRef(onToken);
    onTokenRef.current = onToken;

    useEffect(() => {
        if (!siteKey || typeof window === 'undefined') return;

        let cancelled = false;
        const mountWidget = () => {
            if (cancelled || !containerRef.current || !window.turnstile || widgetIdRef.current) {
                return;
            }
            widgetIdRef.current = window.turnstile.render(containerRef.current, {
                sitekey: siteKey,
                theme: 'dark',
                callback: (token) => onTokenRef.current(token),
                'expired-callback': () => onTokenRef.current(null),
                'error-callback': () => onTokenRef.current(null),
            });
        };

        const cleanupListener = loadTurnstileScript(mountWidget);
        return () => {
            cancelled = true;
            cleanupListener();
            if (widgetIdRef.current && window.turnstile) {
                window.turnstile.remove(widgetIdRef.current);
                widgetIdRef.current = null;
            }
        };
    }, [siteKey]);

    useEffect(() => {
        if (!siteKey || resetKey === 0) return;
        onTokenRef.current(null);
        if (widgetIdRef.current && window.turnstile) {
            window.turnstile.reset(widgetIdRef.current);
        }
    }, [siteKey, resetKey]);

    if (!siteKey) return null;

    return <div ref={containerRef} data-testid="turnstile-widget" className="min-h-16" />;
}
