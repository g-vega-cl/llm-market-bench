import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { getBenchmarkHistoryFn } from '~/features/portfolios/api/benchmark-server-fn';
import {
    fetchFrontierThemes,
    fetchFutureForces,
    fetchPerformanceHistory,
    fetchPortfolioById,
    fetchPositions,
    fetchTrades,
} from '~/features/portfolios/api/fetch-portfolios';
import { PortfolioDetailPage } from '~/features/portfolios/pages/PortfolioDetailPage';

const getPortfolioData = createServerFn({ method: 'GET' })
    .validator((d: string) => d)
    .handler(async ({ data: portfolioId }: { data: string }) => {
        const [portfolio, positions, history, trades, themes, forces] = await Promise.all([
            fetchPortfolioById(portfolioId),
            fetchPositions(portfolioId),
            fetchPerformanceHistory(portfolioId),
            fetchTrades(portfolioId),
            fetchFrontierThemes(portfolioId),
            fetchFutureForces(portfolioId),
        ]);

        return { portfolio, positions, history, trades, themes, forces };
    });

export const Route = createFileRoute('/portfolios/$portfolioId')({
    loader: ({ params }) => getPortfolioData({ data: params.portfolioId }),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getPortfolioDataFn = useServerFn(getPortfolioData);
    const getBenchmarkDataFn = useServerFn(getBenchmarkHistoryFn);

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
