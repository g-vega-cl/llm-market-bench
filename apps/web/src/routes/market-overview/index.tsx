import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMarketOverviewData } from '~/features/market-overview/api/fetch-market-overview';
import { MarketOverviewPage } from '~/features/market-overview/pages/MarketOverviewPage';

const getMarketOverview = createServerFn({ method: 'GET' })
    .validator((d: { limit?: number } | undefined) => d)
    .handler(async ({ data }) => {
        return fetchMarketOverviewData(data?.limit);
    });

export const Route = createFileRoute('/market-overview/')({
    // Full matrix (~190 rows) so filters never run against a partial slice and flash "no match".
    loader: async () => await getMarketOverview({ data: { limit: undefined } }),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getMarketOverviewFn = useServerFn(getMarketOverview);

    return (
        <MarketOverviewPage
            initialData={initialData}
            fetchFn={() => getMarketOverviewFn({ data: { limit: undefined } })}
        />
    );
}
