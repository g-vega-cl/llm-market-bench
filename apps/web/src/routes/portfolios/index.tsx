import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import {
    fetchAllActivePortfolioPerformance,
    fetchBenchmarkHistory,
    fetchPortfolios,
} from '~/features/portfolios/api/fetch-portfolios';
import { BENCHMARK_OPTIONS } from '~/features/portfolios/components/BenchmarkSelector';
import { PortfoliosPage } from '~/features/portfolios/pages/PortfoliosPage';

const getPortfolios = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchPortfolios();
});

const getComparisonData = createServerFn({ method: 'GET' }).handler(async () => {
    const { portfolios, startDate, endDate } = await fetchAllActivePortfolioPerformance(
        36500, // 100 years (full history)
    );
    const benchmarks = BENCHMARK_OPTIONS.map((opt) => opt.ticker);
    const benchmarkData = await fetchBenchmarkHistory(benchmarks, startDate, endDate);
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
            comparisonFetchFn={() => getComparisonDataFn()}
        />
    );
}
