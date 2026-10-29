import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchLatestMarketBarometer } from '~/features/home/api/fetch-barometer';
import { filterLastBars, isRegularMarketHours } from '~/features/home/api/fetch-intraday-tape';
import type { LiveAgentState } from '~/features/home/components/LiveAgentConsole';
import type { CandlestickBar } from '~/features/home/components/SPYCandlestickChart';
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

interface MarketFeelingRecord {
    market_direction?: string | null;
    why_explanation?: string | null;
    sentiment_label?: string | null;
    sentiment_emoji?: string | null;
    confidence_score?: number | null;
    primary_concern?: string | null;
    secondary_concern?: string | null;
    model_used?: string | null;
    created_at?: string | null;
    trades_summary?: unknown;
}

interface IntradayPayload {
    buys?: number;
    sells?: number;
    action?: 'BUY' | 'SELL' | 'HOLD';
    technicals?: { vwap: number; rsi_14: number; trend: string };
    memories_consulted?: string[];
    bars?: CandlestickBar[];
}

function buildAgentState(
    feeling: MarketFeelingRecord | null,
    payload: IntradayPayload | null,
): LiveAgentState {
    const rawAction = payload?.action;
    const action = rawAction || ((payload?.buys ?? 0) > (payload?.sells ?? 0) ? 'BUY' : 'HOLD');

    return {
        action: action as 'BUY' | 'SELL' | 'HOLD',
        conviction: feeling?.confidence_score ?? 75,
        thought: feeling?.why_explanation || 'Scanning intraday tape and evaluating risk.',
        marketDirection:
            (feeling?.market_direction as 'BULLISH' | 'BEARISH' | 'NEUTRAL') || 'NEUTRAL',
        sentimentLabel: feeling?.sentiment_label || 'Active Surveillance',
        modelUsed: feeling?.model_used || 'Strata Orca',
        lastUpdated: feeling?.created_at ? formatEasternTime(feeling.created_at) : undefined,
        technicals: payload?.technicals || {
            vwap: 582.4,
            rsi_14: 54.2,
            trend: feeling?.market_direction || 'NEUTRAL',
        },
        memoriesConsulted:
            payload?.memories_consulted ||
            (feeling?.primary_concern ? [feeling.primary_concern] : []),
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
        const bars = filterLastBars(tradesPayload?.bars, 60);

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
