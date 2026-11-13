import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import {
    fetchCachedComparisonData,
    fetchPortfolios,
} from '~/features/portfolios/api/fetch-portfolios';
import { BENCHMARK_OPTIONS } from '~/features/portfolios/components/BenchmarkSelector';
import { PortfoliosPage } from '~/features/portfolios/pages/PortfoliosPage';

const getPortfolios = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchPortfolios();
});

const getComparisonData = createServerFn({ method: 'GET' }).handler(async () => {
    const benchmarks = BENCHMARK_OPTIONS.map((opt) => opt.ticker);
    return fetchCachedComparisonData(benchmarks, 36500);
});

export const Route = createFileRoute('/portfolios/')({
    loader: async () => {
        const [portfolios, comparisonData] = await Promise.all([
            getPortfolios(),
            getComparisonData(),
        ]);
        return { portfolios, comparisonData };
    },
    component: RouteComponent,
});

function RouteComponent() {
    const loaderData = Route.useLoaderData();
    const initialData = Array.isArray(loaderData) ? loaderData : loaderData.portfolios;
    const initialComparisonData = Array.isArray(loaderData) ? undefined : loaderData.comparisonData;
    const getPortfoliosFn = useServerFn(getPortfolios);
    const getComparisonDataFn = useServerFn(getComparisonData);

    return (
        <PortfoliosPage
            initialData={initialData}
            initialComparisonData={initialComparisonData}
            fetchFn={() => getPortfoliosFn()}
            comparisonFetchFn={() => getComparisonDataFn()}
        />
    );
}
