import { usePostHog } from '@posthog/react';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { useState } from 'react';
import {
    emptyLeaderboard,
    fetchPortfolioLeaderboard,
    normalizePoints,
    normalizeRows,
    type PortfolioLeaderboard,
} from '~/features/home/api/portfolio-leaderboard';
import { RecipeDeskHomePage } from '~/features/home/pages/RecipeDeskHomePage';
import { forkRecipeFn } from '~/features/recipes/api/fork-recipe';
import { fetchPublicDesk, type PublicDesk } from '~/features/recipes/api/public-board-api';
import { track } from '~/lib/analytics';
import { seo } from '~/lib/seo';

function normalizeDesk(value: unknown): PublicDesk {
    const raw = (value ?? {}) as Partial<PublicDesk>;
    return {
        cards: Array.isArray(raw.cards) ? raw.cards : [],
        feed: Array.isArray(raw.feed) ? raw.feed : [],
        liveCount: Number(raw.liveCount ?? 0),
        beatSpyCount: Number(raw.beatSpyCount ?? 0),
        medianReturnPct: typeof raw.medianReturnPct === 'number' ? raw.medianReturnPct : null,
    };
}

interface HomePayload {
    desk: PublicDesk;
    leaderboard: PortfolioLeaderboard;
}

export function normalizeLeaderboard(value: unknown): PortfolioLeaderboard {
    const raw = (value ?? {}) as Partial<PortfolioLeaderboard>;
    return {
        // Rows carry a nested series array that also crosses the loader boundary;
        // coercing only the outer arrays was the deploy-skew crash of 4be16417.
        rows: normalizeRows(raw.rows),
        spy: normalizePoints(raw.spy),
        medianReturnPct:
            typeof raw.medianReturnPct === 'number' && Number.isFinite(raw.medianReturnPct)
                ? raw.medianReturnPct
                : null,
        trackedCount:
            raw.trackedCount === null || raw.trackedCount === undefined
                ? null
                : Number.isFinite(Number(raw.trackedCount))
                  ? Number(raw.trackedCount)
                  : null,
        windowDays: Number.isFinite(Number(raw.windowDays)) ? Number(raw.windowDays) : 30,
        // An absent payload is an unknown board, not a young one.
        degraded: value == null ? true : Boolean(raw.degraded),
        spyUnavailable: Boolean(raw.spyUnavailable),
    };
}

const EMPTY_DESK: PublicDesk = {
    cards: [],
    feed: [],
    liveCount: 0,
    beatSpyCount: 0,
    medianReturnPct: null,
};

const getHome = createServerFn({ method: 'GET' }).handler(async (): Promise<HomePayload> => {
    // A missing board beats an error page on the front door — including during
    // the window before a migration has been applied.
    const [desk, leaderboard] = await Promise.all([
        fetchPublicDesk().catch(() => EMPTY_DESK),
        fetchPortfolioLeaderboard().catch((error: unknown) => {
            // A missing view and an empty board are different facts: log the first
            // and let the page say "unavailable" instead of "young".
            console.error('[home] portfolio leaderboard unavailable', error);
            return emptyLeaderboard(true);
        }),
    ]);
    return { desk, leaderboard };
});

export const Route = createFileRoute('/')({
    loader: async () => await getHome(),
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
    const payload = (Route.useLoaderData() ?? {}) as Partial<HomePayload>;
    const desk = normalizeDesk(payload.desk);
    const leaderboard = normalizeLeaderboard(payload.leaderboard);
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
        <RecipeDeskHomePage
            desk={desk}
            leaderboard={leaderboard}
            onFork={handleFork}
            forkingId={forkingId}
            error={error}
        />
    );
}
