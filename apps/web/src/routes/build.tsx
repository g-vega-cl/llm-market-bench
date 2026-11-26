import { resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { createFileRoute, redirect } from '@tanstack/react-router';
import {
    fetchRecipeQuotaStatusFn,
    fetchUserRecipesFn,
} from '~/features/recipes/api/recipes-quota-api';
import { BuilderChatPanel } from '~/features/recipes/builder/BuilderChatPanel';
import { CompiledBotWorkspace } from '~/features/recipes/builder/CompiledBotWorkspace';
import { STARTER_RECIPES } from '~/features/recipes/starter-templates';
import { seo } from '~/lib/seo';
import { buildAuthRedirectSearch } from '~/shared/auth/redirect';

export const Route = createFileRoute('/build')({
    validateSearch: (
        search: Record<string, unknown>,
    ): {
        idea?: string;
        recipeId?: string;
        starter?: string;
    } => ({
        idea:
            typeof search.idea === 'string' && search.idea.trim() ? search.idea.trim() : undefined,
        recipeId:
            typeof search.recipeId === 'string' && search.recipeId.trim()
                ? search.recipeId.trim()
                : undefined,
        starter:
            typeof search.starter === 'string' && search.starter.trim()
                ? search.starter.trim()
                : undefined,
    }),
    beforeLoad: ({ context, search }) => {
        if (search.recipeId) {
            throw redirect({
                to: '/recipes/$recipeId',
                params: { recipeId: search.recipeId },
                replace: true,
            });
        }
        // A starter prefill carries real recipe data; gate it behind sign-in so
        // shared links land on the auth card instead of an anonymous studio.
        if (search.starter && !context?.user?.id) {
            throw redirect({
                to: '/login',
                search: buildAuthRedirectSearch(
                    '/build',
                    `?starter=${encodeURIComponent(search.starter)}`,
                ),
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
    const { idea, starter } = Route.useSearch();
    const { initialAtmosphere, initialQuota, initialUserRecipes } = Route.useLoaderData();
    const { user } = Route.useRouteContext();

    // A starter template selected from the public gallery loads deterministically
    // by exact name — no LLM re-compilation, no surprise changes.
    if (starter) {
        const template = STARTER_RECIPES.find((t) => t.name === starter);
        if (template) {
            return (
                <CompiledBotWorkspace
                    initialStrategy={template}
                    initialQuota={initialQuota}
                    initialUserRecipes={initialUserRecipes}
                />
            );
        }
    }

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
