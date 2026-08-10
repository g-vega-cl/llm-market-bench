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
}));

describe('Profile Navigation & Route Migration TDD', () => {
    it('navItems should not contain the posts route', () => {
        const postsItem = navItems.find((item) => item.to === '/posts');
        expect(postsItem).toBeUndefined();
    });

    it('renders authenticated user email at far left linking to /profile', async () => {
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

        const profileLink = await screen.findByText('testuser@example.com');
        expect(profileLink).toBeInTheDocument();
        const anchor = profileLink.closest('a');
        expect(anchor).toHaveAttribute('href', '/profile');
    });
});
