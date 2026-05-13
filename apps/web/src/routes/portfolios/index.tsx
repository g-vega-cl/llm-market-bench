import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import {
    fetchAllActivePortfolioPerformance,
    fetchBenchmarkHistory,
    fetchPortfolios,
} from '~/features/portfolios/api/fetch-portfolios';
import { PortfoliosPage } from '~/features/portfolios/pages/PortfoliosPage';

const getPortfolios = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchPortfolios();
});

const getComparisonData = createServerFn({ method: 'GET' })
    .inputValidator((d: { benchmark: string; maxDays: number }) => d)
    .handler(async ({ data }: { data: { benchmark: string; maxDays: number } }) => {
        const { portfolios, startDate, endDate } = await fetchAllActivePortfolioPerformance(
            data.maxDays,
        );
        const benchmarkData = await fetchBenchmarkHistory([data.benchmark], startDate, endDate);
        return { portfolios, startDate, endDate, benchmarkData };
    });

export const Route = createFileRoute('/portfolios/')({
    loader: async () => await getPortfolios(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getPortfoliosFn = useServerFn(getPortfolios);
    const getComparisonDataFn = useServerFn(getComparisonData);

    return (
        <PortfoliosPage
            initialData={initialData}
            fetchFn={() => getPortfoliosFn()}
            comparisonFetchFn={(benchmark, maxDays) =>
                getComparisonDataFn({ data: { benchmark, maxDays } })
            }
        />
    );
}
