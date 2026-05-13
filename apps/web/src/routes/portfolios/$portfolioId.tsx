import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import {
    fetchBenchmarkHistory,
    fetchPerformanceHistory,
    fetchPortfolioById,
    fetchPositions,
    fetchTrades,
} from '~/features/portfolios/api/fetch-portfolios';
import { PortfolioDetailPage } from '~/features/portfolios/pages/PortfolioDetailPage';

const getPortfolioData = createServerFn({ method: 'GET' })
    .inputValidator((d: string) => d)
    .handler(async ({ data: portfolioId }: { data: string }) => {
        const [portfolio, positions, history, trades] = await Promise.all([
            fetchPortfolioById(portfolioId),
            fetchPositions(portfolioId),
            fetchPerformanceHistory(portfolioId),
            fetchTrades(portfolioId),
        ]);

        return { portfolio, positions, history, trades };
    });

const getBenchmarkData = createServerFn({ method: 'GET' })
    .inputValidator((d: { tickers: string[]; startDate: string; endDate: string }) => d)
    .handler(
        async ({ data }: { data: { tickers: string[]; startDate: string; endDate: string } }) => {
            if (data.tickers.length === 0) return {};
            return fetchBenchmarkHistory(data.tickers, data.startDate, data.endDate);
        },
    );

export const Route = createFileRoute('/portfolios/$portfolioId')({
    loader: ({ params }) => getPortfolioData({ data: params.portfolioId }),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getPortfolioDataFn = useServerFn(getPortfolioData);
    const getBenchmarkDataFn = useServerFn(getBenchmarkData);

    return (
        <PortfolioDetailPage
            initialData={initialData}
            fetchFn={(portfolioId: string) => getPortfolioDataFn({ data: portfolioId })}
            benchmarkFetchFn={(tickers, startDate, endDate) =>
                getBenchmarkDataFn({ data: { tickers, startDate, endDate } })
            }
        />
    );
}
