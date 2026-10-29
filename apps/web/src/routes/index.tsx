import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchLatestMarketBarometer } from '~/features/home/api/fetch-barometer';
import {
    buildAgentState,
    fetchLatestIntradayBars,
    type IntradayPayload,
    isRegularMarketHours,
    type MarketFeelingRecord,
} from '~/features/home/api/fetch-intraday-tape';
import type { HomePageData } from '~/features/home/pages/HomePage';
import { HomePage } from '~/features/home/pages/HomePage';
import {
    type BenchmarkDataPoint,
    fetchAllActivePortfolioPerformance,
    fetchBenchmarkHistory,
    type PortfolioPerformanceItem,
} from '~/features/portfolios/api/fetch-portfolios';
import { isAutoresearchPortfolio, isSystemPortfolio } from '~/features/portfolios/lib/config';
import { fetchLatestMarketFeeling } from '~/features/today/api/fetch-today-data';
import { formatEasternTime } from '~/utils/date';

function mapPortfolioPerformance(p: PortfolioPerformanceItem): HomePageData['portfolios'][number] {
    let todayPct = 0;
    let weekPct = 0;
    let totalEquity = 0;

    if (p.performance.length > 0) {
        const len = p.performance.length;
        const last = p.performance[len - 1].totalEquity;
        const prev = len >= 2 ? p.performance[len - 2].totalEquity : last;
        const first = p.performance[0].totalEquity;

        totalEquity = last;
        todayPct = prev > 0 ? ((last - prev) / prev) * 100 : 0;
        weekPct = first > 0 ? ((last - first) / first) * 100 : 0;
    }

    const cleanName = p.ownerId.split('/').pop() || p.ownerId;
    const displayName = cleanName.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

    return {
        name: displayName,
        todayPct: Number(todayPct.toFixed(2)),
        weekPct: Number(weekPct.toFixed(2)),
        totalEquity,
        isActive: true,
        isAutoResearch: isAutoresearchPortfolio(p.ownerId),
        isSystem: isSystemPortfolio(p.ownerId),
    };
}

function calculateBenchmarkMoves(benchmarkData: BenchmarkDataPoint[]): {
    todayPct: number;
    weekPct: number;
} {
    if (benchmarkData.length < 2) {
        return { todayPct: 0, weekPct: 0 };
    }
    const sortedBench = [...benchmarkData].sort((a, b) => a.date.localeCompare(b.date));
    const last = sortedBench[sortedBench.length - 1].price;
    const prev = sortedBench[sortedBench.length - 2].price;
    const first = sortedBench[0].price;

    const benchToday = prev > 0 ? ((last - prev) / prev) * 100 : 0;
    const benchWeek = first > 0 ? ((last - first) / first) * 100 : 0;

    return {
        todayPct: Number(benchToday.toFixed(2)),
        weekPct: Number(benchWeek.toFixed(2)),
    };
}

function buildFeelingSummary(feeling: MarketFeelingRecord | null, payload: IntradayPayload | null) {
    return {
        sentiment: feeling?.market_direction || 'NEUTRAL',
        summary: feeling?.why_explanation || 'No market feeling available.',
        sentimentLabel: feeling?.sentiment_label || 'Analyzing...',
        sentimentEmoji: feeling?.sentiment_emoji || '🤔',
        confidence: feeling?.confidence_score ?? 50,
        primaryConcern: feeling?.primary_concern || undefined,
        secondaryConcern: feeling?.secondary_concern || undefined,
        modelUsed: feeling?.model_used || undefined,
        lastAnalyzed: feeling?.created_at ? formatEasternTime(feeling.created_at) : undefined,
        buyCount: payload?.buys,
        sellCount: payload?.sells,
    };
}

const getHomepageData = createServerFn({ method: 'GET' }).handler(
    async (): Promise<HomePageData> => {
        const [marketFeeling, portfoliosData, barometer] = await Promise.all([
            fetchLatestMarketFeeling(),
            fetchAllActivePortfolioPerformance(7),
            fetchLatestMarketBarometer(),
        ]);

        const benchmarkRecord = await fetchBenchmarkHistory(
            ['SPY'],
            portfoliosData.startDate,
            portfoliosData.endDate,
        );
        const benchmarkData = benchmarkRecord.SPY || [];

        const portfoliosList = portfoliosData.portfolios
            .filter((p) => !isSystemPortfolio(p.ownerId))
            .map(mapPortfolioPerformance);

        const benchmark = calculateBenchmarkMoves(benchmarkData);
        const tradesPayload = (marketFeeling?.trades_summary as IntradayPayload | null) ?? null;
        const bars = await fetchLatestIntradayBars(marketFeeling);

        return {
            portfolios: portfoliosList,
            benchmark,
            bars,
            agentState: buildAgentState(marketFeeling, tradesPayload),
            isMarketOpen: isRegularMarketHours(),
            feeling: buildFeelingSummary(marketFeeling, tradesPayload),
            barometer,
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
