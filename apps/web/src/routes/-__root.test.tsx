import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
    createMemoryHistory,
    createRootRoute,
    createRouter,
    RouterProvider,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getRootHead, NavLink, navItems, RootDocument } from './__root';

const mockPostHogProvider = vi.fn(({ children }) => <>{children}</>);

vi.mock('~/lib/posthog-client', async (importOriginal) => {
    const actual = await importOriginal<typeof import('~/lib/posthog-client')>();
    return {
        ...actual,
        PostHogLazyBoundary: (props: Record<string, unknown>) => mockPostHogProvider(props),
    };
});

// Mock HeadContent and Scripts so tests don't need a full router context.
// The actual router head() output is covered by the getRootHead() test below.
// Link is left as the real implementation so the NavLink render test works
// with a real RouterProvider.
vi.mock('@tanstack/react-router', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/react-router')>();
    return {
        ...actual,
        HeadContent: () => null,
        Scripts: () => null,
    };
});

function renderWithProviders(ui: React.ReactNode) {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function renderRootDocument(children: React.ReactNode) {
    // Wrap RootDocument in a RouterProvider with a minimal test route so that
    // <Link> and the lazy PostHog boundary have the router context they need.
    const testRoute = createRootRoute({
        component: () => <RootDocument>{children}</RootDocument>,
    });
    const memoryHistory = createMemoryHistory({ initialEntries: ['/'] });
    const router = createRouter({ routeTree: testRoute, history: memoryHistory });
    return renderWithProviders(<RouterProvider router={router} />);
}

describe('Root layout navigation', () => {
    it('navItems should have Portfolios, Memories, and Auto-Research as the first three items', () => {
        expect(navItems[0].label).toBe('Portfolios');
        expect(navItems[1].label).toBe('Memories');
        expect(navItems[2].label).toBe('Auto-Research');
    });

    it('NavLink should render with correct properties and shrink-0 class', async () => {
        const rootRoute = createRootRoute({
            component: () => <NavLink to="/portfolios" label="Portfolios" exact={true} />,
        });

        const memoryHistory = createMemoryHistory({
            initialEntries: ['/'],
        });

        const router = createRouter({
            routeTree: rootRoute,
            history: memoryHistory,
        });

        renderWithProviders(<RouterProvider router={router} />);

        // Wait for router resolution and element to appear
        const link = await screen.findByText('Portfolios');
        expect(link).toBeInTheDocument();
        expect(link.tagName.toLowerCase()).toBe('a');
        expect(link).toHaveAttribute('href', '/portfolios');
        // Validate our specific responsive requirement class
        expect(link).toHaveClass('shrink-0');
        expect(link).toHaveClass('hover:text-accent-hover');
    });
});

describe('RootDocument PostHog configuration', () => {
    beforeEach(() => {
        mockPostHogProvider.mockClear();
    });

    it('wraps children in PostHogLazyBoundary (so posthog-js is never on the critical render path)', async () => {
        renderRootDocument(<div>Test Content</div>);
        await screen.findByText('Test Content');

        // The boundary itself renders synchronously, but it does NOT call
        // posthog.init() at render time — that is deferred to the
        // requestIdleCallback in the boundary's useEffect. In jsdom the
        // idle callback never fires, so the boundary's setClient step is
        // never reached and the real PostHogProvider is never rendered.
        // We assert that the boundary is mounted (proving the integration
        // is wired up) and that it does not crash on its own.
        expect(mockPostHogProvider).toHaveBeenCalled();
    });

    it('does NOT import @posthog/react anywhere in __root.tsx (avoids static posthog-js bundle)', async () => {
        const fs = await import('node:fs');
        const path = await import('node:path');
        const filePath = path.join(__dirname, '__root.tsx');
        const source = fs.readFileSync(filePath, 'utf8');
        // Static `import ... from '@posthog/react'` would pull posthog-js
        // into the main bundle. The lazy boundary uses a custom context.
        expect(source).not.toMatch(/from\s+['"]@posthog\/react['"]/);
    });
});

describe('RootDocument Performance Optimizations', () => {
    it('should render Google Fonts asynchronously with media="print" to prevent render blocking', async () => {
        renderRootDocument(<div>Test Content</div>);
        await screen.findByText('Test Content');

        // Verify the asynchronous font loading trick (check document since it's rendered in head)
        const fontLinks = document.querySelectorAll('link[href*="fonts.googleapis.com/css2"]');
        expect(fontLinks.length).toBeGreaterThan(0);

        // Find the one that has media="print"
        const asyncFontLink = Array.from(fontLinks).find(
            (link) => link.getAttribute('media') === 'print',
        );
        expect(asyncFontLink).toBeTruthy();
    });

    it('does NOT render TanStackRouterDevtools in production builds', async () => {
        // We assert by reading the __root source string and checking the guard wraps
        // the TanStackRouterDevtools usage (so the devtools never ship to production).
        const fs = await import('node:fs');
        const path = await import('node:path');
        const filePath = path.join(__dirname, '__root.tsx');
        const source = fs.readFileSync(filePath, 'utf8');
        expect(source).toMatch(/TanStackRouterDevtools/);
        // The TanStackRouterDevtools import must be lazy (dynamic import) OR the JSX
        // must be guarded by import.meta.env.DEV / .PROD so it never reaches prod bundle.
        const hasJsxGuard =
            /\{import\.meta\.env\.DEV\s*&&\s*[\s\S]*?<TanStackRouterDevtools/.test(source) ||
            /\{import\.meta\.env\.PROD\s*\?\s*null\s*:[\s\S]*?<TanStackRouterDevtools/.test(source);
        const hasLazyImport = /import\(['"]@tanstack\/react-router-devtools['"]\)/.test(source);
        expect(hasJsxGuard || hasLazyImport).toBe(true);
    });

    it('does NOT eagerly initialize posthog-js in module scope (must be lazy)', async () => {
        const fs = await import('node:fs');
        const path = await import('node:path');
        // Read both __root.tsx and the lazy posthog client to verify init is gated
        const rootPath = path.join(__dirname, '__root.tsx');
        const rootSource = fs.readFileSync(rootPath, 'utf8');
        // Root must not call posthog.init() at module top-level
        expect(rootSource).not.toMatch(/posthog\.init\(/);
    });

    it('declares a CSS preload link and a non-blocking stylesheet in the head config', () => {
        // The head() callback is what TanStack Start renders via <HeadContent />.
        // We assert the structure directly so the test does not need a full router.
        const head = getRootHead();
        const preloadLink = head.links.find(
            (l) => l.rel === 'preload' && (l as { as?: string }).as === 'style',
        );
        expect(preloadLink).toBeDefined();

        const stylesheetLink = head.links.find(
            (l) => l.rel === 'stylesheet' && (l as { media?: string }).media === 'print',
        );
        expect(stylesheetLink).toBeDefined();
    });
});
