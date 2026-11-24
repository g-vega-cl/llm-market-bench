import { resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { createFileRoute } from '@tanstack/react-router';
import { fetchRecipeByIdFn } from '~/features/recipes/api/recipes-api';
import {
    fetchRecipeQuotaStatusFn,
    fetchUserRecipesFn,
} from '~/features/recipes/api/recipes-quota-api';
import { fetchLivePortfolioAndRunsFn } from '~/features/recipes/api/recipes-studio-api';
import { BuilderChatPanel } from '~/features/recipes/builder/BuilderChatPanel';
import { CompiledBotWorkspace } from '~/features/recipes/builder/CompiledBotWorkspace';
import { toLiveSummary } from '~/features/recipes/builder/live-summary';
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
    loaderDeps: ({ search }) => ({ recipeId: search.recipeId }),
    loader: async ({ deps, context }) => {
        const initialAtmosphere = resolveAtmospherePhase(new Date(), 'market-et');
        if (!context?.user?.id) {
            return {
                initialAtmosphere,
                initialStrategy: null,
                initialQuota: null,
                initialUserRecipes: [],
                initialLive: null,
            };
        }
        const initialStrategy = deps.recipeId
            ? await fetchRecipeByIdFn({ data: { recipeId: deps.recipeId } }).catch(() => null)
            : null;
        // `fetchRecipeById` strips the id for non-owners, so the live snapshot is
        // only read for the viewer's own bot — never for a shared public recipe, and
        // never for a row whose block would not render.
        const ownedRecipeId = initialStrategy?.id;
        const [initialQuota, initialUserRecipes, initialLive] = await Promise.all([
            fetchRecipeQuotaStatusFn().catch(() => null),
            fetchUserRecipesFn().catch(() => []),
            ownedRecipeId
                ? fetchLivePortfolioAndRunsFn({ data: { recipeId: ownedRecipeId } })
                      .then((snapshot) => toLiveSummary(snapshot))
                      .catch((err: unknown) => {
                          // The block degrades to "history not loaded"; log it so an
                          // outage is never mistaken for a bot with no live turns.
                          console.error('[build] live snapshot read failed; degrading', err);
                          return null;
                      })
                : Promise.resolve(null),
        ]);
        return {
            initialAtmosphere,
            initialStrategy,
            initialQuota,
            initialUserRecipes,
            initialLive,
        };
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Build a trading bot from one sentence | Benchify',
                description:
                    'Describe the bot you want. The builder asks one quick alignment round, then compiles a runnable point-in-time recipe you can edit and backtest.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const { idea } = Route.useSearch();
    const { initialAtmosphere, initialStrategy, initialQuota, initialUserRecipes, initialLive } =
        Route.useLoaderData();
    const { user } = Route.useRouteContext();
    return initialStrategy ? (
        <CompiledBotWorkspace
            key={initialStrategy.id ?? initialStrategy.name}
            initialStrategy={initialStrategy}
            initialQuota={initialQuota}
            initialUserRecipes={initialUserRecipes}
            initialLive={initialLive}
        />
    ) : (
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
