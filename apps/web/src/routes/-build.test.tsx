import {
    createMemoryHistory,
    createRootRoute,
    createRoute,
    createRouter,
    isRedirect,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Route, RouteComponent } from './build';

vi.mock('@tanstack/react-start', () => ({
    createServerFn: () => ({
        handler: (fn: unknown) => fn,
        validator: () => ({ handler: (fn: unknown) => fn }),
    }),
}));

vi.mock('~/features/recipes/api/recipes-quota-api', () => ({
    fetchRecipeQuotaStatusFn: vi.fn(),
    fetchUserRecipesFn: vi.fn(),
}));

vi.mock('~/features/recipes/builder/BuilderChatPanel', () => ({
    BuilderChatPanel: () => <div data-testid="builder-chat" />,
}));

vi.mock('~/features/recipes/builder/CompiledBotWorkspace', () => ({
    CompiledBotWorkspace: ({ initialStrategy }: { initialStrategy: { name: string } }) => (
        <div data-testid="compiled-workspace">{initialStrategy.name}</div>
    ),
}));

type ValidateSearch = (search: Record<string, unknown>) => {
    idea?: string;
    recipeId?: string;
    starter?: string;
};

const validateSearch = Route.options.validateSearch as unknown as ValidateSearch;

function canonicalHref(entry: string): { requested: string; canonical: string } {
    const rootRoute = createRootRoute();
    const buildRoute = createRoute({
        getParentRoute: () => rootRoute,
        path: '/build',
        validateSearch,
    });
    const router = createRouter({
        routeTree: rootRoute.addChildren([buildRoute]),
        history: createMemoryHistory({ initialEntries: [entry] }),
    });
    router.updateLatestLocation();
    const requested = router.latestLocation;
    const canonical = router.buildLocation({
        to: requested.pathname,
        search: true,
        params: true,
        hash: true,
        state: true,
        _includeValidateSearch: true,
    } as never);
    return { requested: requested.publicHref, canonical: canonical.publicHref };
}

function stubRoute(search: ReturnType<ValidateSearch>): void {
    vi.spyOn(Route, 'useSearch').mockReturnValue(search as never);
    vi.spyOn(Route, 'useLoaderData').mockReturnValue({
        initialAtmosphere: 'day',
        initialQuota: null,
        initialUserRecipes: [],
    } as never);
    vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: { id: 'u1' } } as never);
}

afterEach(() => vi.restoreAllMocks());

describe('/build starter prefill', () => {
    it('validates and trims the starter name while leaving absent params undefined', () => {
        expect(validateSearch({ starter: '  Trump & Chips News Momentum  ' })).toEqual({
            idea: undefined,
            recipeId: undefined,
            starter: 'Trump & Chips News Momentum',
        });
        expect(validateSearch({ starter: '   ' })).toEqual({
            idea: undefined,
            recipeId: undefined,
            starter: undefined,
        });
    });

    it('keeps the ampersand-encoded starter URL canonical so SSR issues no redirect', () => {
        const { requested, canonical } = canonicalHref(
            '/build?starter=Trump%20%26%20Chips%20News%20Momentum',
        );
        // The router normalises %20 to '+', but both sides agree: no 307 loop.
        expect(canonical).toBe(requested);
        expect(new URLSearchParams(requested.split('?')[1]).get('starter')).toBe(
            'Trump & Chips News Momentum',
        );
    });

    it('redirects anonymous starter visits to /login carrying the starter in the redirect', async () => {
        let thrown: unknown;
        try {
            await (
                Route.options.beforeLoad as (args: {
                    context: { user?: { id: string } };
                    search: { starter?: string };
                }) => Promise<void>
            )({
                context: {},
                search: { starter: 'Trump & Chips News Momentum' },
            });
        } catch (err) {
            thrown = err;
        }

        expect(isRedirect(thrown)).toBe(true);
        expect((thrown as { options: Record<string, unknown> }).options).toMatchObject({
            to: '/login',
            search: { redirect: '/build?starter=Trump%20%26%20Chips%20News%20Momentum' },
            replace: true,
        });
    });

    it('lets signed-in starter visits through the guard', async () => {
        let err: unknown;
        try {
            await (
                Route.options.beforeLoad as (args: {
                    context: { user?: { id: string } };
                    search: { starter?: string };
                }) => Promise<void>
            )({
                context: { user: { id: 'u1' } },
                search: { starter: 'Trump & Chips News Momentum' },
            });
        } catch (thrown) {
            err = thrown;
        }
        expect(err).toBeUndefined();
    });

    it('opens the exact selected starter in the compiled workspace, not the chat', () => {
        stubRoute({ starter: 'Trump & Chips News Momentum' });
        render(<RouteComponent />);

        expect(screen.getByTestId('compiled-workspace')).toHaveTextContent(
            'Trump & Chips News Momentum',
        );
        expect(screen.queryByTestId('builder-chat')).not.toBeInTheDocument();
    });

    it('falls back to the builder chat when the starter name is unknown', () => {
        stubRoute({ starter: 'Not A Starter' });
        render(<RouteComponent />);

        expect(screen.getByTestId('builder-chat')).toBeInTheDocument();
        expect(screen.queryByTestId('compiled-workspace')).not.toBeInTheDocument();
    });
});
