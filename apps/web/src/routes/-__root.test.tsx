import {
    createMemoryHistory,
    createRootRoute,
    createRouter,
    RouterProvider,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { NavLink, navItems, PostHogAuthSync, RootDocument, Route } from './__root';

const mockPostHogProvider = vi.fn(({ children }) => <>{children}</>);
const mockIdentify = vi.fn();
const mockReset = vi.fn();
const mockGetDistinctId = vi.fn();

vi.mock('@posthog/react', () => ({
    PostHogProvider: (props: Record<string, unknown>) => mockPostHogProvider(props),
    usePostHog: () => ({
        identify: mockIdentify,
        reset: mockReset,
        get_distinct_id: mockGetDistinctId,
    }),
}));

describe('Root layout navigation', () => {
    it('navItems should strictly contain 3 topbar items: Home, Portfolios, and Lab', () => {
        expect(navItems).toHaveLength(3);
        expect(navItems[0]).toEqual({ to: '/', label: 'Home', exact: true });
        expect(navItems[1]).toEqual({ to: '/portfolios', label: 'Portfolios' });
        expect(navItems[2]).toEqual({ to: '/lab', label: 'Lab' });
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

        render(<RouterProvider router={router} />);

        // Wait for router resolution and element to appear
        const link = await screen.findByText('Portfolios');
        expect(link).toBeInTheDocument();
        expect(link.tagName.toLowerCase()).toBe('a');
        expect(link).toHaveAttribute('href', '/portfolios');
        expect(link).toHaveClass('shrink-0');
        expect(link).toHaveClass('voxel-btn');
    });
});

describe('RootDocument PostHog configuration', () => {
    it('should initialize PostHogProvider with the stealthy reverse proxy /p api_host', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: null });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Test Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({
            initialEntries: ['/'],
        });

        const router = createRouter({
            routeTree: testRoute,
            history: memoryHistory,
        });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });

        // Wait for router to resolve and render RootDocument
        await screen.findByText('Test Content');

        expect(mockPostHogProvider).toHaveBeenCalled();
        const props = mockPostHogProvider.mock.calls[0][0] as { options?: { api_host?: string } };
        expect(props.options?.api_host).toBe('/p');
    });

    it('should initialize PostHogProvider with disable_surveys: true to reduce unused JS', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: null });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Test Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({
            initialEntries: ['/'],
        });

        const router = createRouter({
            routeTree: testRoute,
            history: memoryHistory,
        });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });
        await screen.findByText('Test Content');

        expect(mockPostHogProvider).toHaveBeenCalled();
        const props = mockPostHogProvider.mock.calls[
            mockPostHogProvider.mock.calls.length - 1
        ][0] as { options?: { disable_surveys?: boolean } };
        expect(props.options?.disable_surveys).toBe(true);
    });

    it('should initialize PostHogProvider with session recording enabled and privacy masking configured', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: null });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Test Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({
            initialEntries: ['/'],
        });

        const router = createRouter({
            routeTree: testRoute,
            history: memoryHistory,
        });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });
        await screen.findByText('Test Content');

        expect(mockPostHogProvider).toHaveBeenCalled();
        const props = mockPostHogProvider.mock.calls[
            mockPostHogProvider.mock.calls.length - 1
        ][0] as {
            options?: {
                disable_session_recording?: boolean;
                session_recording?: {
                    maskAllInputs?: boolean;
                    maskTextSelector?: string;
                };
            };
        };
        expect(props.options?.disable_session_recording).toBeUndefined();
        expect(props.options?.session_recording).toEqual({
            maskAllInputs: true,
            maskTextSelector: '[data-ph-mask]',
        });
    });

    it('should initialize PostHogProvider with before_send handler that drops CefSharp scanner errors', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: null });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Test Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({
            initialEntries: ['/'],
        });

        const router = createRouter({
            routeTree: testRoute,
            history: memoryHistory,
        });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });
        await screen.findByText('Test Content');

        expect(mockPostHogProvider).toHaveBeenCalled();
        const props = mockPostHogProvider.mock.calls[
            mockPostHogProvider.mock.calls.length - 1
        ][0] as {
            options?: {
                before_send?: (event: unknown) => unknown | null;
            };
        };
        expect(props.options?.before_send).toBeDefined();

        const transformed = props.options?.before_send?.({
            uuid: 'test',
            event: '$exception',
            properties: {
                $exception_level: 'error',
                $exception_list: [
                    {
                        type: 'UnhandledRejection',
                        value: 'Non-Error promise rejection captured with value: Object Not Found Matching Id:3, MethodName:update, ParamCount:4',
                    },
                ],
            },
        });

        expect(transformed).toBeNull();
    });
});

describe('RootDocument Performance Optimizations', () => {
    it('should render Google Fonts asynchronously with media="print" to prevent render blocking', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: null });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Test Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({
            initialEntries: ['/'],
        });

        const router = createRouter({
            routeTree: testRoute,
            history: memoryHistory,
        });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });
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
});

describe('RootDocument PostHog identity synchronization', () => {
    it('should identify authenticated user with UUID and email when distinct_id does not match', async () => {
        mockIdentify.mockClear();
        mockGetDistinctId.mockReturnValue('anon-uuid-999');

        vi.spyOn(Route, 'useRouteContext').mockReturnValue({
            user: { id: 'usr-123', email: 'investor@example.com' },
        });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>App Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({ initialEntries: ['/'] });
        const router = createRouter({
            routeTree: testRoute,
            history: memoryHistory,
        });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });

        await screen.findByText('App Content');

        expect(mockIdentify).toHaveBeenCalledWith('usr-123', {
            email: 'investor@example.com',
        });
    });

    it('should not call posthog.identify if distinct_id already matches user id', async () => {
        mockIdentify.mockClear();
        mockGetDistinctId.mockReturnValue('usr-123');

        vi.spyOn(Route, 'useRouteContext').mockReturnValue({
            user: { id: 'usr-123', email: 'investor@example.com' },
        });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>App Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({ initialEntries: ['/'] });
        const router = createRouter({
            routeTree: testRoute,
            history: memoryHistory,
        });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });

        await screen.findByText('App Content');

        expect(mockIdentify).not.toHaveBeenCalled();
    });

    it('should call posthog.reset when an authenticated user transitions to unauthenticated', () => {
        mockReset.mockClear();
        mockIdentify.mockClear();
        mockGetDistinctId.mockReturnValue('anon-uuid-111');

        const { rerender } = render(
            <PostHogAuthSync user={{ id: 'usr-123', email: 'investor@example.com' }} />,
        );

        expect(mockIdentify).toHaveBeenCalledWith('usr-123', {
            email: 'investor@example.com',
        });

        // User logs out / transitions to null
        rerender(<PostHogAuthSync user={null} />);

        expect(mockReset).toHaveBeenCalled();
    });
});
