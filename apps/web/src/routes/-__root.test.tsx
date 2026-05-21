import {
    createMemoryHistory,
    createRootRoute,
    createRouter,
    RouterProvider,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { NavLink, navItems, RootDocument, Route } from './__root';

const mockPostHogProvider = vi.fn(({ children }) => <>{children}</>);

vi.mock('@posthog/react', () => ({
    PostHogProvider: (props: Record<string, unknown>) => mockPostHogProvider(props),
}));

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

        render(<RouterProvider router={router} />);

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

        render(<RouterProvider router={router} />);

        // Wait for router to resolve and render RootDocument
        await screen.findByText('Test Content');

        expect(mockPostHogProvider).toHaveBeenCalled();
        const callArgs = mockPostHogProvider.mock.calls[0][0];
        expect(callArgs.options.api_host).toBe('/p');
    });
});
