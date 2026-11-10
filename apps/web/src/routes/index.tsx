import { usePostHog } from '@posthog/react';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchLatestMarketBarometer } from '~/features/home/api/fetch-barometer';
import {
    buildAgentState,
    fetchLatestIntradayBars,
    fetchTodayLiveTraderTrades,
    type IntradayPayload,
    isRegularMarketHours,
    type MarketFeelingRecord,
} from '~/features/home/api/fetch-intraday-tape';
import { useWindowFocusRefresh } from '~/features/home/hooks/useWindowFocusRefresh';
import type { HomePageData } from '~/features/home/pages/HomePage';
import { HomePage } from '~/features/home/pages/HomePage';
import {
    type BenchmarkDataPoint,
    fetchAllActivePortfolioPerformance,
    fetchBenchmarkHistory,
    fetchLatestBenchmarkQuote,
    type LiveBenchmarkQuote,
    type PortfolioPerformanceItem,
} from '~/features/portfolios/api/fetch-portfolios';
import { isAutoresearchPortfolio, isSystemPortfolio } from '~/features/portfolios/lib/config';
import { fetchLatestMarketFeeling } from '~/features/today/api/fetch-today-data';
import { formatEasternTime, getEasternDate } from '~/utils/date';

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

function mergeLatestBenchmarkQuote(
    points: BenchmarkDataPoint[],
    latestQuote?: { price: number; date: string } | null,
    isMarketOpen = false,
): BenchmarkDataPoint[] {
    if (!latestQuote || latestQuote.price <= 0 || !latestQuote.date) {
        return points;
    }

    const sortedExisting = [...points].sort((a, b) => a.date.localeCompare(b.date));
    const lastExistingDate =
        sortedExisting.length > 0 ? sortedExisting[sortedExisting.length - 1].date : '';

    const merged = [...points];
    const existingIdx = merged.findIndex((p) => p.date === latestQuote.date);

    if (!lastExistingDate || latestQuote.date > lastExistingDate) {
        if (existingIdx !== -1) {
            merged[existingIdx] = { date: latestQuote.date, price: latestQuote.price };
        } else {
            merged.push({ date: latestQuote.date, price: latestQuote.price });
        }
    } else if (latestQuote.date === lastExistingDate && isMarketOpen && existingIdx !== -1) {
        merged[existingIdx] = { date: latestQuote.date, price: latestQuote.price };
    }

    return merged;
}

export function calculateBenchmarkMoves(
    benchmarkData: BenchmarkDataPoint[],
    latestQuote?: { price: number; date: string } | null,
    isMarketOpen = false,
): {
    todayPct: number;
    weekPct: number;
} {
    const points = mergeLatestBenchmarkQuote(benchmarkData, latestQuote, isMarketOpen);
    if (points.length < 2) {
        return { todayPct: 0, weekPct: 0 };
    }
    const sortedBench = points.sort((a, b) => a.date.localeCompare(b.date));
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

        const isMarketOpen = isRegularMarketHours();
        const tradesPayload = (marketFeeling?.trades_summary as IntradayPayload | null) ?? null;
        const [bars, trades, benchmarkRecord] = await Promise.all([
            fetchLatestIntradayBars(marketFeeling),
            fetchTodayLiveTraderTrades('live-spy-trader'),
            fetchBenchmarkHistory(['SPY'], portfoliosData.startDate, portfoliosData.endDate),
        ]);
        const benchmarkData = benchmarkRecord.SPY || [];

        const todayET = getEasternDate();
        let latestQuote: LiveBenchmarkQuote | null = null;

        if (bars.length > 0) {
            const lastBar = bars[bars.length - 1];
            const barDate = getEasternDate(lastBar.time);
            // Only accept bar as live quote if emitted on today's trading day (ET)
            if (lastBar.close > 0 && barDate === todayET) {
                latestQuote = {
                    price: lastBar.close,
                    date: barDate,
                };
            }
        }

        if (!latestQuote) {
            const cacheQuote = await fetchLatestBenchmarkQuote('SPY');
            if (cacheQuote && cacheQuote.date === todayET) {
                latestQuote = cacheQuote;
            }
        }

        const portfoliosList = portfoliosData.portfolios
            .filter((p) => !isSystemPortfolio(p.ownerId))
            .map(mapPortfolioPerformance);

        const benchmark = calculateBenchmarkMoves(benchmarkData, latestQuote, isMarketOpen);

        return {
            portfolios: portfoliosList,
            benchmark,
            bars,
            trades,
            agentState: buildAgentState(marketFeeling, tradesPayload),
            isMarketOpen,
            feeling: buildFeelingSummary(marketFeeling, tradesPayload),
            barometer,
        };
    },
);

export const Route = createFileRoute('/')({
    loader: async () => await getHomepageData(),
    component: RouteComponent,
});

export function RouteComponent() {
    const data = Route.useLoaderData();
    const context = Route.useRouteContext();
    const router = useRouter();
    const posthog = usePostHog();

    useWindowFocusRefresh({
        onRefresh: () => {
            router.invalidate();
        },
        posthog,
    });

    return <HomePage data={{ ...data, currentUser: context?.user ?? null }} />;
}
