/// <reference types="vite/client" />

import { cn, GlobalBackground } from '@llm-market-bench/ui-design-system';
import { PostHogProvider, usePostHog } from '@posthog/react';
import {
    createRootRoute,
    HeadContent,
    Link,
    Outlet,
    Scripts,
    useRouter,
} from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';
import { createServerFn } from '@tanstack/react-start';
import type { PostHog } from 'posthog-js';
import { type ReactNode, useEffect, useRef } from 'react';
import { DefaultCatchBoundary } from '~/components/ui/DefaultCatchBoundary';
import { NotFound } from '~/components/ui/NotFound';
import { SiteFooter } from '~/features/legal/SiteFooter';
import { ensureWeeklyTokensFn } from '~/features/recipes/api/token-ledger';
import { getAuthServerClient, getPublicAuthConfig } from '~/lib/auth';
import { setRuntimeAuthConfig } from '~/lib/auth-client';
import { getPublicArchiveDbConfig, setRuntimeArchiveDbConfig } from '~/lib/db';
import { QueryClientProviderWrapper } from '~/lib/query-client';
import { canonicalUrl, seo } from '~/lib/seo';
import { consumePendingGoogleAuth } from '~/shared/auth/pending-auth';
import { posthogBeforeSend } from '~/utils/posthog-filter';
import { warmRouteChunks } from '~/utils/route-warmup';
import appCss from '../styles/app.css?url';

if (typeof window !== 'undefined') {
    window.addEventListener('unhandledrejection', (event) => {
        const reason = event?.reason;
        const text =
            typeof reason === 'string'
                ? reason
                : typeof reason?.message === 'string'
                  ? reason.message
                  : String(reason ?? '');
        if (
            typeof text === 'string' &&
            text.includes('Object Not Found Matching Id') &&
            text.includes('MethodName:')
        ) {
            event.preventDefault();
            event.stopImmediatePropagation?.();
            console.warn(
                '[PostHog] Suppressed CefSharp scanner rejection (dropped from telemetry):',
                text,
            );
        }
    });
}

export type AuthUser = {
    id: string;
    email: string;
};

export type PublicRuntimeConfig = {
    archiveDbUrl: string;
    archiveDbAnonKey: string;
    authUrl: string;
    authAnonKey: string;
    posthogProjectToken: string;
    posthogHost: string;
};

const fetchRootContext = createServerFn({ method: 'GET' }).handler(
    async (): Promise<{ user: AuthUser | null; publicConfig: PublicRuntimeConfig }> => {
        const archiveConfig = getPublicArchiveDbConfig();
        const authConfig = getPublicAuthConfig();
        const publicConfig: PublicRuntimeConfig = {
            archiveDbUrl: archiveConfig.url,
            archiveDbAnonKey: archiveConfig.anonKey,
            authUrl: authConfig.url,
            authAnonKey: authConfig.anonKey,
            posthogProjectToken:
                process.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN ||
                process.env.PUBLIC_POSTHOG_PROJECT_TOKEN ||
                '',
            posthogHost:
                process.env.VITE_PUBLIC_POSTHOG_HOST ||
                process.env.PUBLIC_POSTHOG_HOST ||
                'https://us.i.posthog.com',
        };

        try {
            const authClient = getAuthServerClient();
            const { data, error } = await authClient.auth.getUser();

            if (error || !data?.user?.id || !data?.user?.email) {
                return { user: null, publicConfig };
            }

            return {
                user: {
                    id: data.user.id,
                    email: data.user.email,
                },
                publicConfig,
            };
        } catch (err) {
            console.warn('[fetchUser] Failed to resolve auth user; defaulting to guest:', err);
            return { user: null, publicConfig };
        }
    },
);

function hydrateBrowserPublicConfig(publicConfig?: PublicRuntimeConfig) {
    if (typeof window === 'undefined' || !publicConfig) return;
    setRuntimeArchiveDbConfig({
        url: publicConfig.archiveDbUrl,
        anonKey: publicConfig.archiveDbAnonKey,
    });
    setRuntimeAuthConfig({
        url: publicConfig.authUrl,
        anonKey: publicConfig.authAnonKey,
    });
}

/**
 * Silent no-op PostHog client passed when no project token is configured so
 * `usePostHog()` consumers never hit `posthog-js` uninitialized console errors.
 */
const NOOP_POSTHOG_CLIENT = {
    __loaded: false,
    capture: () => undefined,
    captureException: () => undefined,
    identify: () => undefined,
    reset: () => undefined,
    get_distinct_id: () => '',
    reloadFeatureFlags: () => undefined,
    isFeatureEnabled: () => undefined,
    getFeatureFlag: () => undefined,
    getFeatureFlagResult: () => undefined,
    onFeatureFlags: () => () => undefined,
    featureFlags: {
        hasLoadedFlags: false,
        getFlags: () => [],
    },
} as unknown as PostHog;

export const Route = createRootRoute({
    beforeLoad: async () => {
        const rootContext = await fetchRootContext();
        hydrateBrowserPublicConfig(rootContext.publicConfig);
        return rootContext;
    },
    head: () => ({
        meta: [
            {
                charSet: 'utf-8',
            },
            {
                name: 'viewport',
                content: 'width=device-width, initial-scale=1',
            },
            ...seo({
                title: 'Benchify — build and backtest trading bots',
                description:
                    'Describe a trading bot in one sentence, backtest it on point-in-time news, and see how it holds up. Paper cash only, with the results left on the record.',
                keywords:
                    'trading bot builder, LLM benchmark, backtesting, paper trading, Benchify',
            }),
        ],
        links: [
            { rel: 'stylesheet', href: appCss },
            { rel: 'icon', href: '/favicon.ico', sizes: '16x16 32x32 48x48' },
            { rel: 'icon', href: '/icon.svg', type: 'image/svg+xml' },
            { rel: 'apple-touch-icon', href: '/apple-touch-icon.png', sizes: '180x180' },
        ],
    }),
    errorComponent: (props) => {
        return (
            <RootDocument>
                <DefaultCatchBoundary {...props} />
            </RootDocument>
        );
    },
    notFoundComponent: () => <NotFound />,
    component: RootComponent,
});

export function useIdleRouteWarmup() {
    const router = useRouter();

    useEffect(() => {
        if (typeof window === 'undefined') return;

        const win = window as Window & {
            requestIdleCallback?: (cb: () => void, options?: { timeout: number }) => number;
            cancelIdleCallback?: (id: number) => void;
        };

        const schedule =
            typeof win.requestIdleCallback === 'function'
                ? (cb: () => void) => win.requestIdleCallback?.(cb, { timeout: 2000 }) ?? 0
                : (cb: () => void) => window.setTimeout(cb, 50);

        const cancel =
            typeof win.cancelIdleCallback === 'function'
                ? (id: number) => win.cancelIdleCallback?.(id)
                : (id: number) => window.clearTimeout(id);

        const controller = new AbortController();
        const handle = schedule(() => {
            void warmRouteChunks(router, controller.signal);
        });

        return () => {
            controller.abort();
            cancel(handle);
        };
    }, [router]);
}

function RootComponent() {
    useIdleRouteWarmup();
    return (
        <RootDocument>
            <QueryClientProviderWrapper>
                <Outlet />
            </QueryClientProviderWrapper>
        </RootDocument>
    );
}

export function BriefcaseIcon() {
    return (
        <svg
            className="w-4 h-4 shrink-0"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <rect x="2" y="7" width="20" height="14" rx="1" />
            <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <path d="M2 12h20" />
        </svg>
    );
}

export function BeakerIcon() {
    return (
        <svg
            className="w-4 h-4 shrink-0"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M9 3h6" />
            <path d="M10 3v5.2L4.2 18.2A2 2 0 0 0 6 21h12a2 2 0 0 0 1.8-2.8L14 8.2V3" />
            <path d="M6.5 15h11" />
        </svg>
    );
}

export function RecipeIcon() {
    return (
        <svg
            className="w-4 h-4 shrink-0"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M4 6h16" />
            <path d="M4 12h10" />
            <path d="M4 18h13" />
            <path d="M18 16v4" />
            <path d="M16 18h4" />
        </svg>
    );
}

export function LoginIcon() {
    return (
        <svg
            className="w-4 h-4 shrink-0"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
            <polyline points="10 17 15 12 10 7" />
            <line x1="15" y1="12" x2="3" y2="12" />
        </svg>
    );
}

export function LogoutIcon() {
    return (
        <svg
            className="w-4 h-4 shrink-0"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
    );
}

export const navItems = [
    { to: '/', label: 'B', ariaLabel: 'Home', exact: true },
    { to: '/recipes', label: <RecipeIcon />, ariaLabel: 'Recipes' },
    { to: '/lab', label: <BeakerIcon />, ariaLabel: 'Lab' },
];

export function NavLink({
    to,
    label,
    ariaLabel,
    exact,
}: {
    to: string;
    label: ReactNode;
    ariaLabel: string;
    exact?: boolean;
}) {
    const isLogo = typeof label === 'string' && label === 'B';
    return (
        <Link
            to={to}
            aria-label={ariaLabel}
            activeProps={{
                className: 'bg-accent text-voxel-trough',
            }}
            inactiveProps={{
                className: 'bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated',
            }}
            activeOptions={{ exact }}
            className={cn(
                'voxel-btn inline-flex items-center justify-center h-9 w-9 shrink-0',
                isLogo && 'font-mono',
            )}
        >
            {label}
        </Link>
    );
}

function isPostHogReady(posthog: unknown): boolean {
    return (posthog as { __loaded?: boolean } | null | undefined)?.__loaded !== false;
}

function capturePendingGoogleAuth(posthog: {
    capture?: (eventName: string, properties?: Record<string, unknown>) => unknown;
}) {
    if (typeof posthog.capture !== 'function') return;
    const provider = consumePendingGoogleAuth();
    if (!provider) return;
    posthog.capture('auth_completed', { provider });
}

type TokenSyncRouter = { invalidate: () => Promise<void> };

/**
 * One idempotent weekly refill per tab per day, and a router refetch only when a
 * grant actually landed — a no-op refill must not re-run every loader.
 */
async function syncWeeklyTokens(userId: string, router: TokenSyncRouter): Promise<void> {
    const key = `benchify:tokens-synced:${userId}:${new Date().toISOString().slice(0, 10)}`;
    try {
        if (window.sessionStorage.getItem(key) === '1') return;
    } catch {
        // Storage unavailable: fall through, the RPC decides.
    }
    try {
        const result = await ensureWeeklyTokensFn();
        try {
            window.sessionStorage.setItem(key, '1');
        } catch {
            // Session storage unavailable: the RPC is idempotent anyway.
        }
        if (result?.applied) await router.invalidate();
    } catch (error) {
        console.error('Weekly token refill failed', error);
    }
}

export function PostHogAuthSync({ user: userProp }: { user?: AuthUser | null } = {}) {
    const routeContext = Route.useRouteContext();
    const user = userProp !== undefined ? userProp : routeContext?.user;
    const posthog = usePostHog();
    const prevUserIdRef = useRef<string | null>(null);

    // Weekly token top-up. The engine sweeps every account on Monday, but a tab
    // left open across the week boundary never re-runs a load-time refill, so
    // re-sync when the tab regains focus as well.
    const router = useRouter();
    useEffect(() => {
        if (!user?.id) return;
        const userId = user.id;
        const run = () => {
            void syncWeeklyTokens(userId, router);
        };
        run();
        window.addEventListener('focus', run);
        return () => window.removeEventListener('focus', run);
    }, [user?.id, router]);

    useEffect(() => {
        if (!posthog) return;

        const sync = () => {
            if (!isPostHogReady(posthog)) return false;

            if (user?.id) {
                if (posthog.get_distinct_id?.() !== user.id) {
                    posthog.identify?.(user.id, {
                        email: user.email,
                    });
                }
                capturePendingGoogleAuth(posthog);
                prevUserIdRef.current = user.id;
            } else if (prevUserIdRef.current && !user) {
                posthog.reset?.();
                prevUserIdRef.current = null;
            }
            return true;
        };

        if (sync()) return;

        // PostHogProvider runs init() in its own useEffect (after child effects);
        // yield one macrotask on cold full-page loads (e.g. OAuth callback 307)
        // so identify() and auth_completed do not drop before __loaded is true.
        const timerId = window.setTimeout(() => {
            sync();
        }, 0);
        return () => window.clearTimeout(timerId);
    }, [user, posthog]);

    return null;
}

export function RootDocument({ children }: { children: ReactNode }) {
    const context = Route.useRouteContext() as
        | { user?: AuthUser | null; publicConfig?: PublicRuntimeConfig }
        | undefined;
    const user = context?.user;
    const publicConfig = context?.publicConfig;
    const router = useRouter();
    const canonical = canonicalUrl(router.state.location.pathname);

    hydrateBrowserPublicConfig(publicConfig);

    const posthogApiKey =
        import.meta.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN ||
        publicConfig?.posthogProjectToken ||
        '';
    const posthogHost =
        import.meta.env.VITE_PUBLIC_POSTHOG_HOST ||
        publicConfig?.posthogHost ||
        'https://us.i.posthog.com';

    const appShell = (
        <>
            <nav
                className={cn(
                    'flex items-center gap-3 px-6 py-3',
                    'bg-voxel-surface border-b-2 border-voxel-bevel-lo shadow-md',
                    'sticky top-0 z-50',
                    'text-sm font-bold uppercase tracking-widest',
                )}
            >
                <div className="flex items-center gap-2">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            label={item.label}
                            ariaLabel={item.ariaLabel}
                            exact={item.exact}
                        />
                    ))}
                </div>

                <div className="ml-auto flex items-center shrink-0">
                    {user ? (
                        <Link
                            to="/logout"
                            aria-label="Logout"
                            title="Logout"
                            className="voxel-btn inline-flex items-center justify-center h-9 w-9 shrink-0 bg-voxel-trough text-danger hover:bg-danger/10"
                        >
                            <LogoutIcon />
                        </Link>
                    ) : (
                        <Link
                            to="/login"
                            aria-label="Login"
                            title="Login"
                            className="voxel-btn inline-flex items-center justify-center h-9 w-9 shrink-0 bg-accent text-voxel-trough hover:bg-accent-hover"
                        >
                            <LoginIcon />
                        </Link>
                    )}
                </div>
            </nav>
            <GlobalBackground />
            <main id="main-content" className="flex-1 flex flex-col">
                {children}
            </main>
            <SiteFooter />
            <TanStackRouterDevtools position="bottom-right" />
            <Scripts />
        </>
    );

    return (
        <html lang="en">
            <head>
                <HeadContent />
                <link rel="canonical" href={canonical} />
                <meta property="og:url" content={canonical} />
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    rel="stylesheet"
                    href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
                    media="print"
                    suppressHydrationWarning
                    onLoad={(e) => {
                        e.currentTarget.media = 'all';
                    }}
                />
                <noscript suppressHydrationWarning>
                    <link
                        rel="stylesheet"
                        href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
                    />
                </noscript>
            </head>
            <body className="min-h-svh flex flex-col">
                {posthogApiKey ? (
                    <PostHogProvider
                        apiKey={posthogApiKey}
                        options={{
                            api_host: typeof window !== 'undefined' ? '/p' : posthogHost,
                            ui_host: 'https://us.posthog.com',
                            defaults: '2025-05-24',
                            autocapture: true,
                            // No PostHog cookie or localStorage: analytics state lives
                            // in page memory, so nothing persistent is written before a
                            // visitor asks us to. Signed-in users stay whole because
                            // PostHogAuthSync re-identifies on every load.
                            persistence: 'memory',
                            capture_exceptions: {
                                capture_unhandled_errors: true,
                                capture_unhandled_rejections: true,
                                capture_console_errors: true,
                            },
                            enable_recording_console_log: true,
                            logs: {
                                captureConsoleLogs: true,
                            },
                            debug: import.meta.env.DEV,
                            session_recording: {
                                maskAllInputs: true,
                                maskTextSelector: '[data-ph-mask]',
                            },
                            disable_surveys: true,
                            before_send: posthogBeforeSend,
                        }}
                    >
                        <PostHogAuthSync user={user} />
                        {appShell}
                    </PostHogProvider>
                ) : (
                    <PostHogProvider client={NOOP_POSTHOG_CLIENT}>
                        <PostHogAuthSync user={user} />
                        {appShell}
                    </PostHogProvider>
                )}
            </body>
        </html>
    );
}
