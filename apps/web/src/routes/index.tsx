import { usePostHog } from '@posthog/react';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { useState } from 'react';
import { RecipeDeskHomePage } from '~/features/home/pages/RecipeDeskHomePage';
import { forkRecipeFn } from '~/features/recipes/api/fork-recipe';
import { fetchPublicDesk, type PublicDesk } from '~/features/recipes/api/public-board-api';
import { track } from '~/lib/analytics';
import { seo } from '~/lib/seo';

const EMPTY_DESK: PublicDesk = {
    cards: [],
    feed: [],
    liveCount: 0,
    beatSpyCount: 0,
    medianReturnPct: null,
};

const getDesk = createServerFn({ method: 'GET' }).handler(async (): Promise<PublicDesk> => {
    try {
        return await fetchPublicDesk();
    } catch {
        // An empty desk beats an error page on the front door — including during
        // the window before the public-stats migration has been applied.
        return EMPTY_DESK;
    }
});

export const Route = createFileRoute('/')({
    loader: async () => await getDesk(),
    head: () => ({
        meta: [
            ...seo({
                title: 'Benchify — build a trading bot from one sentence',
                description:
                    'Describe a strategy and get a recipe that runs three times a day on point-in-time news. Paper cash only, two free backtests a day, three live bots.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const desk = Route.useLoaderData();
    const router = useRouter();
    const posthog = usePostHog();
    const [forkingId, setForkingId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleFork = async (recipeId: string) => {
        setForkingId(recipeId);
        setError(null);
        try {
            const created = await forkRecipeFn({ data: { recipeId } });
            track(posthog, 'recipe_forked', { recipeId });
            await router.navigate({ to: '/recipes', search: { recipeId: created.id } });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Fork failed';
            if (/unauthorized|sign in/i.test(message)) {
                await router.navigate({ to: '/login', search: { redirect: '/recipes' } });
                return;
            }
            setError(message);
        } finally {
            setForkingId(null);
        }
    };

    return (
        <RecipeDeskHomePage desk={desk} onFork={handleFork} forkingId={forkingId} error={error} />
    );
}
