/// <reference types="vite/client" />

import { Badge, cn, GlobalBackground } from '@llm-market-bench/ui-design-system';
import { PostHogProvider, usePostHog } from '@posthog/react';
import { createRootRoute, HeadContent, Link, Outlet, Scripts } from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';
import { createServerFn } from '@tanstack/react-start';
import { type ReactNode, useEffect, useRef } from 'react';
import { DefaultCatchBoundary } from '~/components/ui/DefaultCatchBoundary';
import { NotFound } from '~/components/ui/NotFound';
import { QueryClientProviderWrapper } from '~/lib/query-client';
import { seo } from '~/lib/seo';
import { getSupabaseServerClient } from '~/lib/supabase';
import { posthogBeforeSend } from '~/utils/posthog-filter';
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

const fetchUser = createServerFn({ method: 'GET' }).handler(async (): Promise<AuthUser | null> => {
    const supabase = getSupabaseServerClient();
    const { data, error: _error } = await supabase.auth.getUser();

    if (!data.user?.id || !data.user?.email) {
        return null;
    }

    return {
        id: data.user.id,
        email: data.user.email,
    };
});

export const Route = createRootRoute({
    beforeLoad: async () => {
        const user = await fetchUser();

        return {
            user,
        };
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
                title: 'Benchify, LLM Market Benchmarking',
                description: `Benchify is a LLM Market Benchmarking platform`,
            }),
        ],
        links: [{ rel: 'stylesheet', href: appCss }],
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

function RootComponent() {
    return (
        <RootDocument>
            <QueryClientProviderWrapper>
                <Outlet />
            </QueryClientProviderWrapper>
        </RootDocument>
    );
}

export const navItems = [
    { to: '/', label: 'B', exact: true },
    { to: '/portfolios', label: 'Portfolios' },
    { to: '/lab', label: 'Lab' },
];

export function NavLink({ to, label, exact }: { to: string; label: string; exact?: boolean }) {
    const isLogo = label === 'B';
    return (
        <Link
            to={to}
            aria-label={isLogo ? 'Home' : undefined}
            activeProps={{
                className: 'bg-accent text-boxel-trough',
            }}
            inactiveProps={{
                className: 'bg-boxel-surface text-boxel-ink hover:bg-boxel-elevated',
            }}
            activeOptions={{ exact }}
            className={cn(
                'voxel-btn py-1.5 text-xs font-black uppercase tracking-widest shrink-0',
                isLogo ? 'px-2.5 font-mono' : 'px-3.5',
            )}
        >
            {label}
        </Link>
    );
}

export function PostHogAuthSync({ user: userProp }: { user?: AuthUser | null } = {}) {
    const routeContext = Route.useRouteContext();
    const user = userProp !== undefined ? userProp : routeContext?.user;
    const posthog = usePostHog();
    const prevUserIdRef = useRef<string | null>(null);

    useEffect(() => {
        if (!posthog) return;

        if (user?.id) {
            if (posthog.get_distinct_id?.() !== user.id) {
                posthog.identify?.(user.id, {
                    email: user.email,
                });
            }
            prevUserIdRef.current = user.id;
        } else if (prevUserIdRef.current && !user) {
            posthog.reset?.();
            prevUserIdRef.current = null;
        }
    }, [user, posthog]);

    return null;
}

export function RootDocument({ children }: { children: ReactNode }) {
    const { user } = Route.useRouteContext();

    return (
        <html lang="en">
            <head>
                <HeadContent />
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
            <body>
                <PostHogProvider
                    apiKey={import.meta.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN || ''}
                    options={{
                        api_host:
                            typeof window !== 'undefined'
                                ? '/p'
                                : import.meta.env.VITE_PUBLIC_POSTHOG_HOST ||
                                  'https://us.i.posthog.com',
                        ui_host: 'https://us.posthog.com',
                        defaults: '2025-05-24',
                        capture_exceptions: true,
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
                    <nav
                        className={cn(
                            'flex flex-wrap items-center gap-3 px-6 py-3',
                            'bg-boxel-surface border-b-2 border-boxel-bevel-lo shadow-md',
                            'sticky top-0 z-50',
                            'text-sm font-bold uppercase tracking-widest',
                        )}
                    >
                        <div className="flex items-center gap-2 flex-wrap">
                            {navItems.map((item) => (
                                <NavLink
                                    key={item.to}
                                    to={item.to}
                                    label={item.label}
                                    exact={item.exact}
                                />
                            ))}
                        </div>

                        <div className="ml-auto flex items-center gap-3 shrink-0">
                            {user && (
                                <Link
                                    to="/profile"
                                    className="shrink-0 hover:opacity-80 transition-opacity"
                                >
                                    <Badge
                                        variant="soft"
                                        size="sm"
                                        colorScheme="neutral"
                                        className="normal-case tracking-normal cursor-pointer"
                                    >
                                        {user.email}
                                    </Badge>
                                </Link>
                            )}
                            {user ? (
                                <Link
                                    to="/logout"
                                    className="voxel-btn inline-flex items-center justify-center font-bold bg-boxel-trough text-danger hover:bg-danger/10 px-3 py-1.5 text-xs uppercase tracking-widest"
                                >
                                    Logout
                                </Link>
                            ) : (
                                <Link
                                    to="/login"
                                    className="voxel-btn inline-flex items-center justify-center font-bold bg-accent text-boxel-trough hover:bg-accent-hover px-3 py-1.5 text-xs uppercase tracking-widest"
                                >
                                    Login
                                </Link>
                            )}
                        </div>
                    </nav>
                    <GlobalBackground />
                    {children}
                    <TanStackRouterDevtools position="bottom-right" />
                    <Scripts />
                </PostHogProvider>
            </body>
        </html>
    );
}
