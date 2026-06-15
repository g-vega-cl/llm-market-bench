import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import type { HomePageData } from '~/features/home/pages/HomePage';
import { HomePage } from '~/features/home/pages/HomePage';
import {
    fetchAllActivePortfolioPerformance,
    fetchBenchmarkHistory,
} from '~/features/portfolios/api/fetch-portfolios';
import { isAutoresearchPortfolio } from '~/features/portfolios/lib/config';
import { fetchLatestMarketFeeling } from '~/features/today/api/fetch-today-data';
import { formatEasternTime } from '~/utils/date';

const getHomepageData = createServerFn({ method: 'GET' }).handler(
    async (): Promise<HomePageData> => {
        // Fetch initial data concurrently
        const [marketFeeling, portfoliosData] = await Promise.all([
            fetchLatestMarketFeeling(),
            fetchAllActivePortfolioPerformance(7),
        ]);

        // Fetch benchmark now that we have the dates
        const benchmarkRecord = await fetchBenchmarkHistory(
            ['SPY'],
            portfoliosData.startDate,
            portfoliosData.endDate,
        );
        const benchmarkData = benchmarkRecord.SPY || [];

        // Calculate Individual Portfolio Performance
        const portfoliosList = portfoliosData.portfolios.map((p) => {
            let todayPct = 0;
            let weekPct = 0;
            let totalEquity = 0;

            if (p.performance.length > 0) {
                // performance is sorted by date ascending from fetchAllActivePortfolioPerformance
                const len = p.performance.length;
                const last = p.performance[len - 1].totalEquity;
                const prev = len >= 2 ? p.performance[len - 2].totalEquity : last;
                const first = p.performance[0].totalEquity;

                totalEquity = last;
                todayPct = prev > 0 ? ((last - prev) / prev) * 100 : 0;
                weekPct = first > 0 ? ((last - first) / first) * 100 : 0;
            }

            // Extract a clean name from ownerId if it contains slashes (e.g., 'org/Claude-3-Opus' -> 'Claude-3-Opus')
            const cleanName = p.ownerId.split('/').pop() || p.ownerId;
            // Add spaces before numbers and capitalize to make it look like a model name
            const displayName = cleanName
                .replace(/-/g, ' ')
                .replace(/\b\w/g, (c) => c.toUpperCase());

            return {
                name: displayName,
                todayPct: Number(todayPct.toFixed(2)),
                weekPct: Number(weekPct.toFixed(2)),
                totalEquity,
                isActive: true,
                isAutoResearch: isAutoresearchPortfolio(p.ownerId),
            };
        });

        // Calculate Benchmark Performance
        let benchToday = 0;
        let benchWeek = 0;
        if (benchmarkData.length >= 2) {
            // Sort by date just in case
            const sortedBench = [...benchmarkData].sort((a, b) => a.date.localeCompare(b.date));
            const last = sortedBench[sortedBench.length - 1].price;
            const prev = sortedBench[sortedBench.length - 2].price;
            const first = sortedBench[0].price;

            benchToday = prev > 0 ? ((last - prev) / prev) * 100 : 0;
            benchWeek = first > 0 ? ((last - first) / first) * 100 : 0;
        }

        return {
            portfolios: portfoliosList,
            benchmark: {
                todayPct: Number(benchToday.toFixed(2)),
                weekPct: Number(benchWeek.toFixed(2)),
            },
            feeling: {
                sentiment: marketFeeling?.market_direction || 'NEUTRAL',
                summary: marketFeeling?.why_explanation || 'No market feeling available.',
                sentimentLabel: marketFeeling?.sentiment_label || 'Analyzing...',
                sentimentEmoji: marketFeeling?.sentiment_emoji || '🤔',
                confidence: marketFeeling?.confidence_score ?? 50,
                primaryConcern: marketFeeling?.primary_concern || undefined,
                secondaryConcern: marketFeeling?.secondary_concern || undefined,
                modelUsed: marketFeeling?.model_used || undefined,
                lastAnalyzed: marketFeeling?.created_at
                    ? formatEasternTime(marketFeeling.created_at)
                    : undefined,
            },
        };
    },
);

export const Route = createFileRoute('/')({
    loader: async () => await getHomepageData(),
    component: RouteComponent,
});

function RouteComponent() {
    const data = Route.useLoaderData();
    return <HomePage data={data} />;
}
