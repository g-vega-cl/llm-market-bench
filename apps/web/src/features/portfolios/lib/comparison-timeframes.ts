import type { BenchmarkDataPoint, ComparisonPayload } from '../api/fetch-portfolios';

export type ComparisonTimeframe = '7d' | '30d' | '90d' | 'all';

export const COMPARISON_TIMEFRAMES: readonly ComparisonTimeframe[] = [
    '7d',
    '30d',
    '90d',
    'all',
] as const;

export interface TimeframeSlice {
    portfolios: {
        portfolioId: string;
        ownerId: string;
        performance: { date: string; totalEquity: number; value: number }[];
    }[];
    benchmarkData: Record<string, BenchmarkDataPoint[]>;
}

export function computeTimeframeSlice(
    comparisonData: ComparisonPayload | undefined,
    tf: ComparisonTimeframe,
    now?: Date,
): TimeframeSlice {
    if (!comparisonData?.portfolios) {
        return { portfolios: [], benchmarkData: {} };
    }

    const referenceDate =
        now ??
        (comparisonData.endDate
            ? new Date(`${comparisonData.endDate.split('T')[0]}T00:00:00Z`)
            : new Date());

    const cutoffDateStr = (() => {
        if (tf === 'all') return '0000-01-01';
        const days = tf === '7d' ? 7 : tf === '30d' ? 30 : 90;
        const cutoff = new Date(
            Date.UTC(
                referenceDate.getUTCFullYear(),
                referenceDate.getUTCMonth(),
                referenceDate.getUTCDate() - days,
            ),
        );
        return cutoff.toISOString().split('T')[0];
    })();

    const portfolios = comparisonData.portfolios.map((portfolio) => {
        const filteredPerf = portfolio.performance.filter((p) => p.date >= cutoffDateStr);
        if (filteredPerf.length === 0) {
            return {
                portfolioId: portfolio.portfolioId,
                ownerId: portfolio.ownerId,
                performance: [],
            };
        }

        const firstEquity = filteredPerf[0].totalEquity;
        const performance = filteredPerf.map((p) => ({
            date: p.date,
            totalEquity: p.totalEquity,
            value: firstEquity > 0 ? ((p.totalEquity - firstEquity) / firstEquity) * 100 : 0,
        }));

        return {
            portfolioId: portfolio.portfolioId,
            ownerId: portfolio.ownerId,
            performance,
        };
    });

    const getReturnPct = (p: { performance: { value: number }[] }) => {
        if (!p.performance || p.performance.length === 0) return -Infinity;
        const val = p.performance[p.performance.length - 1]?.value;
        return typeof val === 'number' && !Number.isNaN(val) ? val : -Infinity;
    };

    portfolios.sort((a, b) => {
        const aVal = getReturnPct(a);
        const bVal = getReturnPct(b);
        if (bVal !== aVal) return bVal - aVal;
        return a.ownerId.localeCompare(b.ownerId);
    });

    const benchmarkData: Record<string, BenchmarkDataPoint[]> = {};
    if (comparisonData.benchmarkData) {
        for (const [ticker, points] of Object.entries(comparisonData.benchmarkData)) {
            benchmarkData[ticker] = points.filter((p) => p.date >= cutoffDateStr);
        }
    }

    return { portfolios, benchmarkData };
}

export function precomputeAllTimeframes(
    comparisonData: ComparisonPayload | undefined,
    now?: Date,
): Record<ComparisonTimeframe, TimeframeSlice> {
    return {
        '7d': computeTimeframeSlice(comparisonData, '7d', now),
        '30d': computeTimeframeSlice(comparisonData, '30d', now),
        '90d': computeTimeframeSlice(comparisonData, '90d', now),
        all: computeTimeframeSlice(comparisonData, 'all', now),
    };
}
