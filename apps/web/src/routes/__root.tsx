/// <reference types="vite/client" />

import { Badge, Button, cn } from '@llm-market-bench/ui-design-system';
import { createRootRoute, HeadContent, Link, Outlet, Scripts } from '@tanstack/react-router';
import type * as React from 'react';
import { lazy, Suspense } from 'react';
import { DefaultCatchBoundary } from '~/components/ui/DefaultCatchBoundary';
import { NotFound } from '~/components/ui/NotFound';
import { PostHogLazyBoundary } from '~/lib/posthog-client';
import { QueryClientProviderWrapper } from '~/lib/query-client';
import { seo } from '~/lib/seo';
import { useCurrentUser } from '~/lib/use-current-user';
import appCss from '../styles/app.css?url';

// Devtools are never bundled in production. The lazy() call short-circuits
// to a noop component when running under import.meta.env.PROD, and the
// underlying @tanstack/react-router-devtools module is only fetched in dev.
const TanStackRouterDevtools = lazy(() =>
    import.meta.env.PROD
        ? Promise.resolve({ default: () => null })
        : import('@tanstack/react-router-devtools').then((m) => ({
              default: m.TanStackRouterDevtools,
          })),
);

/**
 * Exported so tests can render the head meta/links without spinning up the
 * full router. The Route below uses the same definition.
 */
export function getRootHead() {
    return {
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
        links: [
            // Preload the bundled CSS so the browser fetches it in parallel with
            // the JS chunk, and the non-blocking stylesheet link below flips the
            // media to "all" without re-fetching.
            { rel: 'preload', as: 'style', href: appCss },
            { rel: 'stylesheet', href: appCss, media: 'print' as const },
        ],
    };
}

export const Route = createRootRoute({
    head: getRootHead,
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
        <QueryClientProviderWrapper>
            <RootDocument>
                <Outlet />
            </RootDocument>
        </QueryClientProviderWrapper>
    );
}

// Exported so regression tests can render the production layout without
// an outer QueryClientProvider. The test asserts the provider scope is
// correct (it must cover the nav, not just the outlet).
export { RootComponent };

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

function NavAuthControls() {
    const { data: user, isLoading } = useCurrentUser();

    if (isLoading || !user) {
        return (
            <Link to="/login">
                <Button variant="solid" size="sm" className="uppercase tracking-widest">
                    Login
                </Button>
            </Link>
        );
    }

    return (
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
    );
}

export function RootDocument({ children }: { children: React.ReactNode }) {
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
                <PostHogLazyBoundary>
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
                            <NavAuthControls />
                        </div>
                    </nav>
                    {children}
                    {import.meta.env.DEV && (
                        <Suspense fallback={null}>
                            <TanStackRouterDevtools position="bottom-right" />
                        </Suspense>
                    )}
                </PostHogLazyBoundary>
                <Scripts />
            </body>
        </html>
    );
}
