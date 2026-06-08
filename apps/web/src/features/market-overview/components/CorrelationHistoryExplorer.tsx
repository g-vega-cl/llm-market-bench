import { Card } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { fetchPairHistory, type PairHistoryPoint } from '../api/fetch-pair-history';
import { etfDescriptions } from '../utils/etf-descriptions';
import { PairProgressionChart } from './PairProgressionChart';

function mapHistoryPoint(
    h: PairHistoryPoint,
    timeframe: '7d' | '30d' | '60d' | '90d',
): PairHistoryPoint {
    switch (timeframe) {
        case '7d':
            return {
                run_date: h.run_date,
                pearson_corr: h.pearson_corr_7d ?? null,
                spearman_corr: h.spearman_corr_7d ?? null,
                returns_a_90d: h.returns_a_7d ?? null,
                returns_b_90d: h.returns_b_7d ?? null,
            };
        case '30d':
            return {
                run_date: h.run_date,
                pearson_corr: h.pearson_corr_30d ?? null,
                spearman_corr: h.spearman_corr_30d ?? null,
                returns_a_90d: h.returns_a_30d ?? null,
                returns_b_90d: h.returns_b_30d ?? null,
            };
        case '60d':
            return {
                run_date: h.run_date,
                pearson_corr: h.pearson_corr_60d ?? null,
                spearman_corr: h.spearman_corr_60d ?? null,
                returns_a_90d: h.returns_a_60d ?? null,
                returns_b_90d: h.returns_b_60d ?? null,
            };
        default:
            return h;
    }
}

interface CorrelationHistoryExplorerProps {
    tickers: string[];
    initialPair?: { tickerA: string; tickerB: string } | null;
    onFetchHistory?: (tickerA: string, tickerB: string) => Promise<PairHistoryPoint[]>;
}

export function CorrelationHistoryExplorer({
    tickers,
    initialPair = null,
    onFetchHistory = fetchPairHistory,
}: CorrelationHistoryExplorerProps) {
    const [tickerA, setTickerA] = React.useState<string>('');
    const [tickerB, setTickerB] = React.useState<string>('');
    const [history, setHistory] = React.useState<PairHistoryPoint[]>([]);
    const [loading, setLoading] = React.useState<boolean>(false);
    const [error, setError] = React.useState<string | null>(null);
    const [timeframe, setTimeframe] = React.useState<'7d' | '30d' | '60d' | '90d'>('90d');

    const mappedHistory = React.useMemo(() => {
        return history.map((h) => mapHistoryPoint(h, timeframe));
    }, [history, timeframe]);

    // Sort tickers alphabetically for clean dropdown lists
    const sortedTickers = React.useMemo(() => {
        return [...tickers].sort();
    }, [tickers]);

    // Handle deep-linking from initialPair prop
    React.useEffect(() => {
        if (initialPair) {
            setTickerA(initialPair.tickerA);
            setTickerB(initialPair.tickerB);
        }
    }, [initialPair]);

    // Trigger history load when both tickers are chosen
    React.useEffect(() => {
        if (!tickerA || !tickerB) return;
        if (tickerA === tickerB) {
            setError('Please select two different assets to compare.');
            setHistory([]);
            return;
        }

        let isMounted = true;
        const loadHistory = () => {
            setLoading(true);
            setError(null);
            onFetchHistory(tickerA, tickerB)
                .then((data) => {
                    if (!isMounted) return;
                    setHistory(data);
                    if (data.length === 0) {
                        setError('No historical correlation data found for this pair.');
                    }
                    setLoading(false);
                })
                .catch((err) => {
                    if (!isMounted) return;
                    const errMsg =
                        err instanceof Error
                            ? err.message
                            : 'Failed to retrieve historical progression.';
                    setError(errMsg);
                    setLoading(false);
                });
        };

        loadHistory();

        return () => {
            isMounted = false;
        };
    }, [tickerA, tickerB, onFetchHistory]);

    // Quick jump recommendations
    const quickJumps = [
        { label: '🪙 Crypto Decoupling', a: 'BTCUSD', b: 'ETHUSD' },
        { label: '⚖️ Equities vs Bonds', a: 'QQQ', b: 'TLT' },
        { label: '🛡️ Safe Havens', a: 'SPY', b: 'GLD' },
        { label: '🛢️ Commodities Shift', a: 'USO', b: 'GLD' },
    ];

    const handleQuickJump = (a: string, b: string) => {
        // Only set if they are valid tickers in the universe
        if (tickers.includes(a) && tickers.includes(b)) {
            setTickerA(a);
            setTickerB(b);
        }
    };

    // Calculate premium metrics from history
    const stats = React.useMemo(() => {
        if (mappedHistory.length === 0) return null;

        const validCorrs = mappedHistory
            .map((h) => h.pearson_corr)
            .filter((c): c is number => c !== null);

        if (validCorrs.length === 0) return null;

        // 1. Average Correlation
        const avgCorr = validCorrs.reduce((sum, c) => sum + c, 0) / validCorrs.length;

        // 2. Correlation Volatility (Standard Deviation)
        const variance =
            validCorrs.reduce((sum, c) => sum + (c - avgCorr) ** 2, 0) / validCorrs.length;
        const stdDev = Math.sqrt(variance);

        // 3. Maximum Decoupling Point (correlation closest to 0 or most negative)
        const maxDecouplingPoint = mappedHistory.reduce((best, curr) => {
            if (curr.pearson_corr === null) return best;
            if (best.pearson_corr === null) return curr;
            return Math.abs(curr.pearson_corr) < Math.abs(best.pearson_corr) ? curr : best;
        }, mappedHistory[0]);

        return {
            avgCorr,
            stdDev,
            maxDecouplingPoint,
            totalWeeks: mappedHistory.length,
        };
    }, [mappedHistory]);

    return (
        <div className="space-y-8 animate-slide-up">
            {/* Control Panel Card */}
            <Card
                variant="glass"
                padding="lg"
                className="rounded-3xl shadow-xl border border-zinc-200/50 dark:border-zinc-800/80"
            >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                    <h3 className="text-xl font-black text-zinc-950 dark:text-white uppercase tracking-tight">
                        Historical Progression Explorer
                    </h3>
                    <div className="flex gap-1 p-1 bg-zinc-100/50 dark:bg-zinc-800/80 rounded-xl border border-zinc-200/50 dark:border-zinc-700/50">
                        {(['7d', '30d', '60d', '90d'] as const).map((tf) => (
                            <button
                                key={tf}
                                type="button"
                                onClick={() => setTimeframe(tf)}
                                className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all duration-150 cursor-pointer ${
                                    timeframe === tf
                                        ? 'bg-blue-500 text-white shadow-sm'
                                        : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
                                }`}
                            >
                                {tf.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
                    {/* Selector A */}
                    <div className="space-y-2">
                        <label
                            htmlFor="select-asset-a"
                            className="text-xs font-black uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
                        >
                            Select Asset A
                        </label>
                        <select
                            id="select-asset-a"
                            value={tickerA}
                            onChange={(e) => setTickerA(e.target.value)}
                            className="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 text-zinc-850 dark:text-zinc-100"
                        >
                            <option value="">-- Choose Ticker --</option>
                            {sortedTickers.map((ticker) => (
                                <option key={ticker} value={ticker} disabled={ticker === tickerB}>
                                    {ticker}
                                    {etfDescriptions[ticker] ? ` — ${etfDescriptions[ticker]}` : ''}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Selector B */}
                    <div className="space-y-2">
                        <label
                            htmlFor="select-asset-b"
                            className="text-xs font-black uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
                        >
                            Select Asset B
                        </label>
                        <select
                            id="select-asset-b"
                            value={tickerB}
                            onChange={(e) => setTickerB(e.target.value)}
                            className="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 text-zinc-850 dark:text-zinc-100"
                        >
                            <option value="">-- Choose Ticker --</option>
                            {sortedTickers.map((ticker) => (
                                <option key={ticker} value={ticker} disabled={ticker === tickerA}>
                                    {ticker}
                                    {etfDescriptions[ticker] ? ` — ${etfDescriptions[ticker]}` : ''}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Quick Jumps */}
                <div className="mt-6 pt-6 border-t border-zinc-100 dark:border-zinc-800/80">
                    <span className="text-[10px] font-black uppercase tracking-wider text-zinc-400 dark:text-zinc-500 block mb-3">
                        Featured Regime Jumps
                    </span>
                    <div className="flex flex-wrap gap-2">
                        {quickJumps.map((jump) => (
                            <button
                                key={jump.label}
                                type="button"
                                onClick={() => handleQuickJump(jump.a, jump.b)}
                                className={`px-4 py-2 text-xs font-bold rounded-xl border transition-all duration-150 cursor-pointer ${
                                    tickerA === jump.a && tickerB === jump.b
                                        ? 'bg-blue-500 border-blue-500 text-white shadow-lg'
                                        : 'bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                                }`}
                            >
                                {jump.label}
                            </button>
                        ))}
                    </div>
                </div>
            </Card>

            {/* Content States */}
            {loading && (
                <div className="flex flex-col items-center justify-center py-24 space-y-4">
                    <div className="w-12 h-12 rounded-full border-4 border-zinc-200 dark:border-zinc-800 border-t-blue-500 animate-spin" />
                    <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest">
                        Fetching historical progression series...
                    </span>
                </div>
            )}

            {error && !loading && (
                <div className="p-8 bg-amber-500/10 border border-amber-500/20 rounded-3xl text-center">
                    <span className="text-2xl block mb-2">⚠️</span>
                    <p className="text-sm font-semibold text-amber-600 dark:text-amber-400">
                        {error}
                    </p>
                </div>
            )}

            {!tickerA || !tickerB ? (
                <div className="p-16 border-2 border-dashed border-zinc-200 dark:border-zinc-850 rounded-3xl text-center">
                    <span className="text-3xl block mb-3 animate-float">📈</span>
                    <h4 className="text-sm font-black text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                        Select an asset pair to view historical progression
                    </h4>
                    <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">
                        Pick two tickers or click one of the quick jumps above to begin tracking
                        historical decoupling.
                    </p>
                </div>
            ) : null}

            {timeframe === '7d' && history.length > 0 && !loading && !error && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-start gap-3 text-amber-600 dark:text-amber-400 animate-slide-up">
                    <span className="text-lg">⚠️</span>
                    <div className="text-xs">
                        <span className="font-bold block mb-0.5">
                            7-Day Correlation Disclaimer:
                        </span>
                        Pearson and Spearman correlations calculated over 7 days (approx. 5 trading
                        days) are highly sensitive to short-term price movements and can exhibit
                        significant noise and volatility. Use with caution for structural
                        diversification decisions.
                    </div>
                </div>
            )}

            {history.length > 0 && !loading && !error && (
                <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
                    {/* Visual Chart */}
                    <div className="xl:col-span-3">
                        <PairProgressionChart
                            data={mappedHistory}
                            tickerA={tickerA}
                            tickerB={tickerB}
                        />
                    </div>

                    {/* Statistical Summary Panel */}
                    {stats && (
                        <div className="space-y-6">
                            <Card
                                padding="md"
                                className="rounded-3xl shadow-lg border border-zinc-100 dark:border-zinc-800/80"
                            >
                                <h4 className="text-xs font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-widest mb-4">
                                    Historical Statistics
                                </h4>

                                <div className="space-y-4">
                                    {/* Average Correlation */}
                                    <div>
                                        <span className="text-[10px] font-black uppercase text-zinc-400 dark:text-zinc-500 block mb-1">
                                            Average Correlation
                                        </span>
                                        <div className="text-2xl font-black font-mono text-zinc-900 dark:text-white">
                                            {stats.avgCorr.toFixed(3)}
                                        </div>
                                        <span
                                            className={`text-[10px] font-bold ${
                                                Math.abs(stats.avgCorr) < 0.2
                                                    ? 'text-emerald-500'
                                                    : Math.abs(stats.avgCorr) > 0.6
                                                      ? 'text-red-500'
                                                      : 'text-zinc-500'
                                            }`}
                                        >
                                            {Math.abs(stats.avgCorr) < 0.2
                                                ? 'Highly Uncorrelated Regime'
                                                : Math.abs(stats.avgCorr) > 0.6
                                                  ? 'Strong Relationship'
                                                  : 'Moderately Diverged'}
                                        </span>
                                    </div>

                                    {/* Correlation Volatility */}
                                    <div>
                                        <span className="text-[10px] font-black uppercase text-zinc-400 dark:text-zinc-500 block mb-1">
                                            Correlation Volatility (σ)
                                        </span>
                                        <div className="text-2xl font-black font-mono text-zinc-900 dark:text-white">
                                            {stats.stdDev.toFixed(3)}
                                        </div>
                                        <span className="text-[10px] font-bold text-zinc-500">
                                            {stats.stdDev < 0.15
                                                ? 'Extremely Stable Trend'
                                                : 'High Regime Instability'}
                                        </span>
                                    </div>

                                    {/* Maximum Decoupling Point */}
                                    <div>
                                        <span className="text-[10px] font-black uppercase text-zinc-400 dark:text-zinc-500 block mb-1">
                                            Max Decoupling Event
                                        </span>
                                        <div className="text-sm font-black text-blue-500">
                                            r = {stats.maxDecouplingPoint.pearson_corr?.toFixed(3)}
                                        </div>
                                        <span className="text-[10px] font-bold text-zinc-500 block">
                                            Observed on:{' '}
                                            {new Date(
                                                stats.maxDecouplingPoint.run_date,
                                            ).toLocaleDateString('en-US', {
                                                month: 'short',
                                                day: 'numeric',
                                                year: 'numeric',
                                                timeZone: 'UTC',
                                            })}
                                        </span>
                                    </div>

                                    {/* Total Observations */}
                                    <div>
                                        <span className="text-[10px] font-black uppercase text-zinc-400 dark:text-zinc-500 block mb-1">
                                            Timeline Duration
                                        </span>
                                        <div className="text-sm font-bold text-zinc-800 dark:text-zinc-200">
                                            {stats.totalWeeks} consecutive weeks
                                        </div>
                                    </div>
                                </div>
                            </Card>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
