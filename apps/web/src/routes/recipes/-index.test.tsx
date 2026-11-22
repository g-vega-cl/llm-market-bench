import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RecipeGalleryPage } from '~/features/recipes/pages/RecipeGalleryPage';
import { Route, RouteComponent } from './index';

vi.mock('@tanstack/react-start', () => ({
    createServerFn: () => ({
        handler: (fn: unknown) => fn,
        validator: () => ({ handler: (fn: unknown) => fn }),
    }),
}));

vi.mock('~/features/recipes/pages/RecipeDashboardPage', () => ({
    RecipeDashboardPage: () => <div data-testid="mock-dashboard" />,
}));

vi.mock('~/features/recipes/api/recipes-api', () => ({
    fetchRecentBacktestJobsFn: vi.fn(),
}));

vi.mock('~/features/recipes/api/recipes-quota-api', () => ({
    fetchRecipeQuotaStatusFn: vi.fn(),
    fetchUserRecipesFn: vi.fn(),
}));

vi.mock('@tanstack/react-router', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/react-router')>();
    return {
        ...actual,
        Link: ({ to, children, ...rest }: { to: string; children: React.ReactNode }) => (
            <a href={to} {...rest}>
                {children}
            </a>
        ),
    };
});

type HeadTag = { name?: string; content?: string; title?: string };

describe('Recipe gallery (public /recipes)', () => {
    it('shows read-only example templates without per-card Sign in to fork buttons', () => {
        render(<RecipeGalleryPage />);
        expect(screen.getByText('Trump & Chips News Momentum')).toBeInTheDocument();
        expect(screen.queryByText('Sign in to fork')).not.toBeInTheDocument();
    });

    it('shows a single primary CTA to /build and a subtle link to /recipes-demo', () => {
        render(<RecipeGalleryPage />);
        expect(screen.getByText('Start Building Your Bot →').closest('a')).toHaveAttribute(
            'href',
            '/build',
        );
        expect(screen.getByText('or see a sample backtest').closest('a')).toHaveAttribute(
            'href',
            '/recipes-demo',
        );
    });
});

describe('Recipes route', () => {
    it('describes recipes in its SEO metadata', () => {
        const head = Route.options.head as unknown as () => { meta: HeadTag[] };
        const description = head().meta.find((tag) => tag.name === 'description')?.content;
        expect(description).toMatch(/one LLM call/i);
    });

    it('renders the gallery instead of the dashboard when nobody is signed in', () => {
        vi.spyOn(Route, 'useLoaderData').mockReturnValue({
            recentBacktests: [],
            initialQuota: null,
            initialUserRecipes: [],
        } as unknown as ReturnType<typeof Route.useLoaderData>);
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({} as never);

        render(<RouteComponent />);

        expect(screen.queryByTestId('mock-dashboard')).not.toBeInTheDocument();
        expect(screen.getByText('Trump & Chips News Momentum')).toBeInTheDocument();
    });

    it('renders the dashboard for a signed-in user', () => {
        vi.spyOn(Route, 'useLoaderData').mockReturnValue({
            recentBacktests: [],
            initialQuota: null,
            initialUserRecipes: [],
        } as unknown as ReturnType<typeof Route.useLoaderData>);
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: { id: 'u1' } } as never);

        render(<RouteComponent />);

        expect(screen.getByTestId('mock-dashboard')).toBeInTheDocument();
    });
});
