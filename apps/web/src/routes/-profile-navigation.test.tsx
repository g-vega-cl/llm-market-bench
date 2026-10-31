import {
    createMemoryHistory,
    createRootRoute,
    createRouter,
    RouterProvider,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { navItems, RootDocument, Route as RootRoute } from './__root';

const mockPostHogProvider = vi.fn(({ children }) => <>{children}</>);

vi.mock('@posthog/react', () => ({
    PostHogProvider: (props: Record<string, unknown>) => mockPostHogProvider(props),
    usePostHog: () => ({
        identify: vi.fn(),
        reset: vi.fn(),
        get_distinct_id: vi.fn(),
    }),
}));

describe('Profile Navigation & Route Migration TDD', () => {
    it('navItems should not contain the posts route', () => {
        const postsItem = navItems.find((item) => item.to === '/posts');
        expect(postsItem).toBeUndefined();
    });

    it('does not render user email when logged in, and keeps logout on same row without flex-wrap', async () => {
        vi.spyOn(RootRoute, 'useRouteContext').mockReturnValue({
            user: { email: 'testuser@example.com' },
        });

        const testRoute = createRootRoute({
            component: () => (
                <RootDocument>
                    <div>Page Content</div>
                </RootDocument>
            ),
        });

        const memoryHistory = createMemoryHistory({ initialEntries: ['/'] });
        const router = createRouter({ routeTree: testRoute, history: memoryHistory });

        render(<RouterProvider router={router} />, {
            container: document.documentElement.parentNode as HTMLElement,
        });

        await screen.findByText('Page Content');

        // Email should not be displayed in navbar
        expect(screen.queryByText('testuser@example.com')).toBeNull();

        // Logout button should be present
        const logoutLink = screen.getByRole('link', { name: 'Logout' });
        expect(logoutLink).toBeInTheDocument();
        expect(logoutLink).toHaveAttribute('href', '/logout');

        // Navbar must not have flex-wrap to ensure logout stays on the same row
        const nav = logoutLink.closest('nav');
        expect(nav).toBeInTheDocument();
        expect(nav?.className).not.toContain('flex-wrap');
    });
});
