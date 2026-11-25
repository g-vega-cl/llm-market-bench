import { resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { createFileRoute, redirect } from '@tanstack/react-router';
import {
    fetchRecipeQuotaStatusFn,
    fetchUserRecipesFn,
} from '~/features/recipes/api/recipes-quota-api';
import { BuilderChatPanel } from '~/features/recipes/builder/BuilderChatPanel';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/build')({
    validateSearch: (search: Record<string, unknown>): { idea?: string; recipeId?: string } => ({
        idea:
            typeof search.idea === 'string' && search.idea.trim() ? search.idea.trim() : undefined,
        recipeId:
            typeof search.recipeId === 'string' && search.recipeId.trim()
                ? search.recipeId.trim()
                : undefined,
    }),
    beforeLoad: ({ search }) => {
        if (search.recipeId) {
            throw redirect({
                to: '/recipes/$recipeId',
                params: { recipeId: search.recipeId },
                replace: true,
            });
        }
    },
    loader: async ({ context }) => {
        const initialAtmosphere = resolveAtmospherePhase(new Date(), 'market-et');
        if (!context?.user?.id) {
            return {
                initialAtmosphere,
                initialQuota: null,
                initialUserRecipes: [],
            };
        }
        const [initialQuota, initialUserRecipes] = await Promise.all([
            fetchRecipeQuotaStatusFn().catch(() => null),
            fetchUserRecipesFn().catch(() => []),
        ]);
        return {
            initialAtmosphere,
            initialQuota,
            initialUserRecipes,
        };
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Build a trading bot | Benchify',
                description:
                    'Benchify turns one sentence into a runnable trading bot recipe, then lets you backtest it on point-in-time news before you switch it Live.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const { idea } = Route.useSearch();
    const { initialAtmosphere, initialQuota, initialUserRecipes } = Route.useLoaderData();
    const { user } = Route.useRouteContext();
    return (
        <BuilderChatPanel
            idea={idea}
            redirectTo="/build"
            userId={user?.id ?? null}
            initialAtmosphere={initialAtmosphere}
            initialQuota={initialQuota}
            initialUserRecipes={initialUserRecipes}
        />
    );
}
