import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import {
    getHomePayload,
    normalizeDesk,
    normalizeLeaderboard,
} from '~/features/home/api/home-payload';
import type { PortfolioLeaderboard } from '~/features/home/api/portfolio-leaderboard';
import { type Mood, normalizeMood } from '~/features/playground/lib/mood';
import { pickProof } from '~/features/playground/lib/proof';
import { HomePlaygroundPage } from '~/features/playground/pages/HomePlaygroundPage';
import type { PublicDesk } from '~/features/recipes/api/public-board-api';
import { fetchRecipeQuotaStatus } from '~/features/recipes/api/recipes-quota-api';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import { seo } from '~/lib/seo';

interface HomeData {
    desk: PublicDesk;
    leaderboard: PortfolioLeaderboard;
    mood: Mood;
    runsLeft: number | null;
    email: string | null;
    isAuthenticated: boolean;
}

/**
 * The mood read is allowed to fail without taking the page with it: a missing
 * table is an unknown mood, not an error page on the front door.
 */
async function readMood(): Promise<Mood> {
    try {
        const { data, error } = await getDbAdminClient()
            .from('market_feeling')
            .select('market_direction, sentiment_label, confidence_score, created_at')
            .order('created_at', { ascending: false })
            .limit(1)
            .maybeSingle();
        if (error) {
            console.warn('[home] market feeling unavailable', error.message);
            return normalizeMood(null);
        }
        return normalizeMood(data);
    } catch (error) {
        console.warn('[home] market feeling read threw', error);
        return normalizeMood(null);
    }
}

const getHome = createServerFn({ method: 'GET' }).handler(async (): Promise<HomeData> => {
    const auth = getAuthServerClient();
    const {
        data: { user },
    } = await auth.auth.getUser();

    const [payload, mood, quota] = await Promise.all([
        getHomePayload(),
        readMood(),
        user?.id
            ? fetchRecipeQuotaStatus(user.id).catch((error: unknown) => {
                  console.warn('[home] quota unavailable', error);
                  return null;
              })
            : Promise.resolve(null),
    ]);

    const limit = quota?.dailyBacktestLimit;
    const used = quota?.backtestsLast24h ?? 0;
    const runsLeft =
        typeof limit === 'number' && Number.isFinite(limit) ? Math.max(0, limit - used) : null;

    return {
        desk: payload.desk,
        leaderboard: payload.leaderboard,
        mood,
        runsLeft,
        email: user?.email ?? null,
        isAuthenticated: Boolean(user?.id),
    };
});

export const Route = createFileRoute('/')({
    loader: async () => await getHome(),
    head: () => ({
        meta: [
            ...seo({
                title: 'Benchify — build a trading bot from five blocks',
                description:
                    'Stack five blocks, run a backtest, and get a bot that decides every 30 minutes during market hours. Paper cash only, losers published beside winners.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const payload = (Route.useLoaderData() ?? {}) as Partial<HomeData>;
    const desk = normalizeDesk(payload.desk);
    const leaderboard = normalizeLeaderboard(payload.leaderboard);

    return (
        <HomePlaygroundPage
            mood={payload.mood ?? normalizeMood(null)}
            proof={pickProof(leaderboard)}
            desk={desk}
            isAuthenticated={Boolean(payload.isAuthenticated)}
            runsLeft={payload.runsLeft ?? null}
            email={payload.email ?? undefined}
        />
    );
}
