/// <reference types="vite/client" />

import { Badge, Button, cn } from '@llm-market-bench/ui-design-system';
import { PostHogProvider } from '@posthog/react';
import { createRootRoute, HeadContent, Link, Outlet, Scripts } from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';
import { createServerFn } from '@tanstack/react-start';
import posthog from 'posthog-js';
import type * as React from 'react';
import { DefaultCatchBoundary } from '~/components/ui/DefaultCatchBoundary';
import { NotFound } from '~/components/ui/NotFound';
import { QueryClientProviderWrapper } from '~/lib/query-client';
import { seo } from '~/lib/seo';
import { getSupabaseServerClient } from '~/lib/supabase';
import appCss from '../styles/app.css?url';

const fetchUser = createServerFn({ method: 'GET' }).handler(async () => {
    const supabase = getSupabaseServerClient();
    const { data, error: _error } = await supabase.auth.getUser();

    if (!data.user?.email) {
        return null;
    }

    return {
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
    { to: '/portfolios', label: 'Portfolios' },
    { to: '/memories', label: 'Memories' },
    { to: '/autoresearch', label: 'Auto-Research' },
    { to: '/', label: 'Today', exact: true },
    { to: '/posts', label: 'Posts' },
    { to: '/concepts', label: 'Concepts' },
    { to: '/how-it-works', label: 'How it Works' },
    { to: '/reasoning', label: 'Reasoning' },
    { to: '/cause-and-effect', label: 'Cause & Effect' },
    { to: '/audits', label: 'Audits' },
    { to: '/market-overview', label: 'Market Overview' },
];

export function NavLink({ to, label, exact }: { to: string; label: string; exact?: boolean }) {
    return (
        <Link
            to={to}
            activeProps={{ className: 'text-accent' }}
            activeOptions={{ exact }}
            className="hover:text-accent-hover transition-colors relative shrink-0"
        >
            {({ isActive }) => (
                <>
                    {label}
                    {isActive && (
                        <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-accent rounded-full" />
                    )}
                </>
            )}
        </Link>
    );
}

// Initialize PostHog client-side only, immediately on JS execution to capture initial page views instantly
if (typeof window !== 'undefined') {
    posthog.init(import.meta.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN || '', {
        api_host: '/p',
        ui_host: 'https://us.posthog.com',
        defaults: '2025-05-24',
        capture_exceptions: true,
        debug: import.meta.env.DEV,
        disable_session_recording: true,
        disable_surveys: true,
    });
}

export function RootDocument({ children }: { children: React.ReactNode }) {
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
                    onLoad={(e) => {
                        e.currentTarget.media = 'all';
                    }}
                />
                <noscript>
                    <link
                        rel="stylesheet"
                        href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
                    />
                </noscript>
            </head>
            <body>
                <PostHogProvider client={posthog}>
                    <nav
                        className={cn(
                            'flex flex-nowrap overflow-x-auto whitespace-nowrap items-center gap-x-6 px-6 py-4',
                            '[&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]',
                            'bg-white/80 dark:bg-zinc-900/80 border-b border-zinc-200 dark:border-zinc-800',
                            'sticky top-0 z-50 backdrop-blur-md',
                            'text-sm font-bold uppercase tracking-widest',
                        )}
                    >
                        {navItems.map((item) => (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                label={item.label}
                                exact={item.exact}
                            />
                        ))}

                        <div className="ml-auto flex items-center gap-4 shrink-0">
                            {user ? (
                                <>
                                    <Badge
                                        variant="soft"
                                        size="sm"
                                        colorScheme="neutral"
                                        className="normal-case tracking-normal"
                                    >
                                        {user.email}
                                    </Badge>
                                    <Link to="/logout">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            colorScheme="danger"
                                            className="uppercase tracking-widest"
                                        >
                                            Logout
                                        </Button>
                                    </Link>
                                </>
                            ) : (
                                <Link to="/login">
                                    <Button
                                        variant="solid"
                                        size="sm"
                                        className="uppercase tracking-widest"
                                    >
                                        Login
                                    </Button>
                                </Link>
                            )}
                        </div>
                    </nav>
                    {children}
                    <TanStackRouterDevtools position="bottom-right" />
                    <Scripts />
                </PostHogProvider>
            </body>
        </html>
    );
}
