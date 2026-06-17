import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchLeaderboard } from '~/features/leaderboard/api/fetch-leaderboard';
import { LeaderboardPage } from '~/features/leaderboard/pages/LeaderboardPage';

const getLeaderboardData = createServerFn({ method: 'GET' }).handler(async () => {
    // Default to 30 days timeframe for SSR/initial load
    return fetchLeaderboard(30);
});

export const Route = createFileRoute('/leaderboard/')({
    loader: async () => await getLeaderboardData(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();

    return <LeaderboardPage initialData={initialData} />;
}
