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

vi.mock('~/features/recipes/pages/RecipeStudioPage', () => ({
    RecipeStudioPage: () => <div data-testid="mock-studio" />,
}));

vi.mock('~/features/recipes/api/recipes-api', () => ({
    fetchRecipeByIdFn: vi.fn(),
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
    it('shows the template catalogue to a logged-out visitor', () => {
        render(<RecipeGalleryPage />);
        expect(screen.getByText('Trump & Chips News Momentum')).toBeInTheDocument();
        expect(screen.getAllByText('Sign in to fork').length).toBeGreaterThan(0);
    });

    it('links the gallery to the builder and the showcase backtest', () => {
        render(<RecipeGalleryPage />);
        expect(screen.getByText('Describe your own').closest('a')).toHaveAttribute(
            'href',
            '/build',
        );
        expect(screen.getByText('See a finished backtest').closest('a')).toHaveAttribute(
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

    it('renders the gallery instead of the studio when nobody is signed in', () => {
        vi.spyOn(Route, 'useLoaderData').mockReturnValue({
            initialStrategy: null,
            recentBacktests: [],
            initialQuota: null,
            initialUserRecipes: [],
        } as unknown as ReturnType<typeof Route.useLoaderData>);
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({} as never);

        render(<RouteComponent />);

        expect(screen.queryByTestId('mock-studio')).not.toBeInTheDocument();
        expect(screen.getByText('Trump & Chips News Momentum')).toBeInTheDocument();
    });

    it('renders the studio for a signed-in user', () => {
        vi.spyOn(Route, 'useLoaderData').mockReturnValue({
            initialStrategy: null,
            recentBacktests: [],
            initialQuota: null,
            initialUserRecipes: [],
        } as unknown as ReturnType<typeof Route.useLoaderData>);
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: { id: 'u1' } } as never);

        render(<RouteComponent />);

        expect(screen.getByTestId('mock-studio')).toBeInTheDocument();
    });
});
