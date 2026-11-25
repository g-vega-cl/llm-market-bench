import { resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchLeaderboardPage } from '~/features/leaderboard/api/fetch-leaderboard';
import { LEADERBOARD_PAGE_SIZE } from '~/features/leaderboard/components/LeaderboardTable';
import { LeaderboardPage } from '~/features/leaderboard/pages/LeaderboardPage';
import { seo } from '~/lib/seo';

const getLeaderboardData = createServerFn({ method: 'GET' }).handler(async () => {
    const [initialData, initialAtmosphere] = await Promise.all([
        fetchLeaderboardPage({
            timeWindowDays: 30,
            category: 'all',
            sortBy: 'composite_score',
            sortDir: 'desc',
            page: 1,
            pageSize: LEADERBOARD_PAGE_SIZE,
        }),
        Promise.resolve(resolveAtmospherePhase(new Date(), 'market-et')),
    ]);
    return { initialData, initialAtmosphere };
});

export const Route = createFileRoute('/leaderboard/')({
    loader: async () => await getLeaderboardData(),
    head: () => ({
        meta: [
            ...seo({
                title: 'Published bot leaderboard | Benchify',
                description:
                    'See how published Benchify trading bots are doing. Paper-cash results, ranking methodology, and point-in-time backtests in one place.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { initialData, initialAtmosphere } = Route.useLoaderData();

    return <LeaderboardPage initialData={initialData} initialAtmosphere={initialAtmosphere} />;
}
