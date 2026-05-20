import {
    createMemoryHistory,
    createRootRoute,
    createRouter,
    RouterProvider,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { NavLink, navItems } from './__root';

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
