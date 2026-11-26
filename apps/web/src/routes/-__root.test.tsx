import {
    createMemoryHistory,
    createRootRoute,
    createRoute,
    createRouter,
    RouterProvider,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
    BeakerIcon,
    BriefcaseIcon,
    LoginIcon,
    LogoutIcon,
    NavLink,
    navItems,
    PostHogAuthSync,
    RootDocument,
    Route,
} from './__root';

const mockPostHogProvider = vi.fn(({ children }) => <>{children}</>);
const mockIdentify = vi.fn();
const mockReset = vi.fn();
const mockGetDistinctId = vi.fn();
const mockCapture = vi.fn();
const mockPostHogClient = {
    __loaded: true,
    identify: mockIdentify,
    reset: mockReset,
    get_distinct_id: mockGetDistinctId,
    capture: mockCapture,
};

vi.mock('@posthog/react', () => ({
    PostHogProvider: (props: Record<string, unknown>) => mockPostHogProvider(props),
    usePostHog: () => mockPostHogClient,
}));

describe('Root layout navigation', () => {
    it('navItems should strictly contain 3 topbar items: B, Recipes icon, and Lab icon', () => {
        expect(navItems).toHaveLength(3);
        expect(navItems[0]).toEqual({ to: '/', label: 'B', ariaLabel: 'Home', exact: true });
        expect(navItems[1].to).toBe('/recipes');
        expect(navItems[1].ariaLabel).toBe('Recipes');
        expect(navItems[2].to).toBe('/lab');
        expect(navItems[2].ariaLabel).toBe('Lab');
    });

    it('NavLink should render with correct properties and shrink-0 class', async () => {
        const rootRoute = createRootRoute({
            component: () => (
                <NavLink to="/recipes" label={<BriefcaseIcon />} ariaLabel="Recipes" exact={true} />
            ),
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
        const link = await screen.findByLabelText('Recipes');
        expect(link).toBeInTheDocument();
        expect(link.tagName.toLowerCase()).toBe('a');
        expect(link).toHaveAttribute('href', '/recipes');
        expect(link).toHaveClass('shrink-0');
        expect(link).toHaveClass('voxel-btn');
        expect(link.querySelector('svg')).toBeInTheDocument();
    });

    it('NavLink for B should render with aria-label="Home" and font-mono class', async () => {
        const rootRoute = createRootRoute({
            component: () => <NavLink to="/" label="B" ariaLabel="Home" exact={true} />,
        });

        const memoryHistory = createMemoryHistory({
            initialEntries: ['/'],
        });

        const router = createRouter({
            routeTree: rootRoute,
            history: memoryHistory,
        });

        render(<RouterProvider router={router} />);

        const link = await screen.findByLabelText('Home');
        expect(link).toBeInTheDocument();
        expect(link).toHaveTextContent('B');
        expect(link).toHaveAttribute('href', '/');
        expect(link).toHaveClass('font-mono');
        expect(link).toHaveClass('voxel-btn');
    });

    it('RootDocument navbar renders B as home button without separate BENCHIFY or Home text buttons', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: null });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({ initialEntries: ['/'] });
        const router = createRouter({ routeTree: testRoute, history: memoryHistory });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });

        await screen.findByText('Content');

        // B should be present as the Home link
        const homeLink = screen.getByRole('link', { name: 'Home' });
        expect(homeLink).toBeInTheDocument();
        expect(homeLink).toHaveTextContent('B');
        expect(homeLink).toHaveAttribute('href', '/');

        // "BENCHIFY" heading text and standalone "HOME" button should NOT exist
        expect(screen.queryByText('BENCHIFY')).toBeNull();
        expect(screen.queryByText('Home')).toBeNull();

        // Site-wide compact disclaimer banner should not be rendered above <main>
        expect(screen.queryByRole('link', { name: 'Learn more' })).toBeNull();
    });

    it('RootDocument navbar renders Logout on the same row without flex-wrap and without user email when authenticated', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({
            user: { id: 'usr-456', email: 'verified@example.com' },
        });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({ initialEntries: ['/'] });
        const router = createRouter({ routeTree: testRoute, history: memoryHistory });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });

        await screen.findByText('Content');

        // Email should NOT be shown in the navbar
        expect(screen.queryByText('verified@example.com')).toBeNull();

        // Logout icon button must be present (SVG, no visible text)
        const logoutLink = screen.getByRole('link', { name: 'Logout' });
        expect(logoutLink).toBeInTheDocument();
        expect(logoutLink).toHaveAttribute('href', '/logout');
        expect(logoutLink.querySelector('svg')).toBeInTheDocument();
        expect(logoutLink).toHaveTextContent('');

        // Navbar must not have flex-wrap to keep logout on the same row
        const nav = logoutLink.closest('nav');
        expect(nav).toBeInTheDocument();
        expect(nav?.className).not.toContain('flex-wrap');
    });

    it('all navbar buttons enforce uniform sizing (h-9 w-9 for nav items and auth icon buttons)', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: null });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({ initialEntries: ['/'] });
        const router = createRouter({ routeTree: testRoute, history: memoryHistory });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });

        await screen.findByText('Content');

        for (const name of ['Home', 'Recipes', 'Lab']) {
            const link = screen.getByRole('link', { name });
            expect(link).toHaveClass('inline-flex', 'items-center', 'justify-center', 'h-9', 'w-9');
        }

        const loginLink = screen.getByRole('link', { name: 'Login' });
        expect(loginLink).toHaveClass(
            'inline-flex',
            'items-center',
            'justify-center',
            'h-9',
            'w-9',
        );
        expect(loginLink.querySelector('svg')).toBeInTheDocument();
        expect(loginLink).toHaveTextContent('');
    });

    it('BriefcaseIcon, BeakerIcon, LoginIcon, and LogoutIcon render recognizable SVGs', () => {
        const { container: briefcaseContainer } = render(<BriefcaseIcon />);
        const briefcaseSvg = briefcaseContainer.querySelector('svg');
        expect(briefcaseSvg).toBeInTheDocument();
        expect(briefcaseSvg?.querySelector('rect')).toBeInTheDocument();
        expect(briefcaseSvg?.querySelectorAll('path').length).toBeGreaterThanOrEqual(2);

        const { container: beakerContainer } = render(<BeakerIcon />);
        const beakerSvg = beakerContainer.querySelector('svg');
        expect(beakerSvg).toBeInTheDocument();
        const beakerPaths = Array.from(beakerSvg?.querySelectorAll('path') ?? []).map((p) =>
            p.getAttribute('d'),
        );
        expect(beakerPaths).toContain('M9 3h6');
        expect(beakerPaths).toContain('M6.5 15h11');
        expect(beakerPaths.length).toBeGreaterThanOrEqual(3);

        const { container: loginContainer } = render(<LoginIcon />);
        expect(loginContainer.querySelector('svg')).toBeInTheDocument();

        const { container: logoutContainer } = render(<LogoutIcon />);
        expect(logoutContainer.querySelector('svg')).toBeInTheDocument();
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

    it('should configure PostHogProvider to capture console errors and record console logs', async () => {
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
                capture_exceptions?: {
                    capture_unhandled_errors?: boolean;
                    capture_unhandled_rejections?: boolean;
                    capture_console_errors?: boolean;
                };
                enable_recording_console_log?: boolean;
                logs?: {
                    captureConsoleLogs?: boolean;
                };
            };
        };
        expect(props.options?.capture_exceptions).toEqual({
            capture_unhandled_errors: true,
            capture_unhandled_rejections: true,
            capture_console_errors: true,
        });
        expect(props.options?.enable_recording_console_log).toBe(true);
        expect(props.options?.logs).toEqual({ captureConsoleLogs: true });
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

    it('captures auth_completed once after a Google OAuth return', () => {
        mockCapture.mockClear();
        window.sessionStorage.setItem('benchify_auth_started', 'google');

        render(<PostHogAuthSync user={{ id: 'usr-123', email: 'investor@example.com' }} />);

        expect(mockCapture).toHaveBeenCalledWith('auth_completed', { provider: 'google' });
        expect(window.sessionStorage.getItem('benchify_auth_started')).toBeNull();
    });

    it('defers identify and auth_completed without dropping the session marker while PostHog is uninitialized', async () => {
        mockCapture.mockClear();
        mockIdentify.mockClear();
        mockGetDistinctId.mockReturnValue('anon-before-oauth');
        mockPostHogClient.__loaded = false;
        window.sessionStorage.setItem('benchify_auth_started', 'google');

        try {
            render(<PostHogAuthSync user={{ id: 'usr-123', email: 'investor@example.com' }} />);

            // Must not consume the marker or drop telemetry before PostHogProvider's useEffect init()
            expect(mockIdentify).not.toHaveBeenCalled();
            expect(mockCapture).not.toHaveBeenCalled();
            expect(window.sessionStorage.getItem('benchify_auth_started')).toBe('google');

            mockPostHogClient.__loaded = true;
            await new Promise((resolve) => window.setTimeout(resolve, 10));

            expect(mockIdentify).toHaveBeenCalledWith('usr-123', {
                email: 'investor@example.com',
            });
            expect(mockCapture).toHaveBeenCalledWith('auth_completed', { provider: 'google' });
            expect(window.sessionStorage.getItem('benchify_auth_started')).toBeNull();
        } finally {
            mockPostHogClient.__loaded = true;
        }
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

    it('should render RootDocument safely when route context is undefined (error state)', async () => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue(undefined as unknown as { user: null });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Error Fallback Content</div>
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

        const content = await screen.findByText('Error Fallback Content');
        expect(content).toBeInTheDocument();
    });

    it('should wrap application children in a semantic <main> landmark element', async () => {
        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div data-testid="page-outlet">Main Page Content</div>
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

        const main = await screen.findByRole('main');
        expect(main).toBeInTheDocument();
        expect(main).toHaveAttribute('id', 'main-content');
        expect(screen.getByTestId('page-outlet')).toBeInTheDocument();
    });

    it('should not prevent default on vite:preloadError so dynamic import errors are not masked as undefined', () => {
        const event = new CustomEvent('vite:preloadError', {
            cancelable: true,
            detail: new Error('Failed to fetch dynamically imported module'),
        });
        window.dispatchEvent(event);
        expect(event.defaultPrevented).toBe(false);
    });

    it('useIdleRouteWarmup warms child route chunks via loadRouteChunk without executing route loaders', async () => {
        const { useIdleRouteWarmup } = await import('./__root');
        const loaderSpy = vi.fn().mockResolvedValue(null);

        const testRoute = createRootRoute({
            component: () => {
                useIdleRouteWarmup();
                return <div>Warmup Active</div>;
            },
        });
        const recipesDemoChild = createRoute({
            getParentRoute: () => testRoute,
            path: '/recipes-demo',
            loader: loaderSpy,
        });

        const memoryHistory = createMemoryHistory({ initialEntries: ['/'] });
        const router = createRouter({
            routeTree: testRoute.addChildren([recipesDemoChild]),
            history: memoryHistory,
        });
        const preloadSpy = vi.spyOn(router, 'preloadRoute').mockResolvedValue(undefined);
        const loadRouteChunkSpy = vi.spyOn(router, 'loadRouteChunk').mockResolvedValue(undefined);
        const getMatchedRoutesSpy = vi.spyOn(router, 'getMatchedRoutes');

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });

        // Wait for idle fallback + inter-chunk yields
        await new Promise((resolve) => setTimeout(resolve, 150));
        expect(getMatchedRoutesSpy).toHaveBeenCalledWith('/recipes-demo');
        const warmedIds = loadRouteChunkSpy.mock.calls.map(([route]) => route.id);
        expect(warmedIds).toContain('/recipes-demo');
        expect(preloadSpy).not.toHaveBeenCalled();
        expect(loaderSpy).not.toHaveBeenCalled();
    });

    it('declares favicon and apple-touch-icon links in Route head', async () => {
        const headResult = await Route.options.head?.({} as never);
        const links = headResult?.links ?? [];

        expect(links).toContainEqual({
            rel: 'icon',
            href: '/favicon.ico',
            sizes: '16x16 32x32 48x48',
        });
        expect(links).toContainEqual({
            rel: 'icon',
            href: '/icon.svg',
            type: 'image/svg+xml',
        });
        expect(links).toContainEqual({
            rel: 'apple-touch-icon',
            href: '/apple-touch-icon.png',
            sizes: '180x180',
        });
    });
});
