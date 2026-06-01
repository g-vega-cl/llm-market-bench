import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchTodayData } from '~/features/today/api/fetch-today-data';
import { fetchTodayHeroData } from '~/features/today/api/fetch-today-hero-data';
import { TodayPage } from '~/features/today/pages/TodayPage';

const getTodayData = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchTodayData();
});

const getTodayHeroData = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchTodayHeroData();
});

export const Route = createFileRoute('/')({
    loader: async () => {
        // Run hero and full data loaders in parallel.
        // The hero returns after one Supabase query (market_feeling) so the
        // MarketStatusHero block can stream to the client first. The full
        // payload streams in separately under <Suspense> boundaries.
        const [hero, data] = await Promise.all([getTodayHeroData(), getTodayData()]);
        return { hero, data };
    },
    component: RouteComponent,
});

function RouteComponent() {
    const { hero, data: initialData } = Route.useLoaderData();
    const getTodayDataFn = useServerFn(getTodayData);

    return <TodayPage hero={hero} initialData={initialData} fetchFn={() => getTodayDataFn()} />;
}
