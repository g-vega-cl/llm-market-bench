import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMarketOverviewData } from '~/features/market-overview/api/fetch-market-overview';
import { MarketOverviewPage } from '~/features/market-overview/pages/MarketOverviewPage';

const getMarketOverview = createServerFn({ method: 'GET' })
    .inputValidator((d: { limit?: number } | undefined) => d)
    .handler(async ({ data }) => {
        return fetchMarketOverviewData(data?.limit);
    });

export const Route = createFileRoute('/market-overview/')({
    loader: async () => await getMarketOverview({ data: { limit: 5 } }),
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
