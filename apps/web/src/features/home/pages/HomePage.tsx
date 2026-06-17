import type { MarketBarometer } from '@llm-market-bench/database';
import { ConfidenceBar } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';

export interface HomePageData {
    portfolios: {
        name: string;
        todayPct: number;
        weekPct: number;
        totalEquity: number;
        isActive: boolean;
        isAutoResearch: boolean;
    }[];
    benchmark: { todayPct: number; weekPct: number };
    feeling: {
        sentiment: string;
        summary: string;
        sentimentLabel?: string;
        sentimentEmoji?: string;
        confidence?: number;
        primaryConcern?: string;
        secondaryConcern?: string;
        modelUsed?: string;
        lastAnalyzed?: string;
    };
    barometer?: MarketBarometer | null;
}

function PortfolioRow({ portfolio }: { portfolio: HomePageData['portfolios'][number] }) {
    const formatMoney = (val: number) => {
        const sign = val < 0 ? '-' : '';
        return `${sign}$${Math.abs(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    return (
        <tr className="hover:bg-white/5 transition-colors duration-200">
            <td className="px-3 py-2 md:px-4 md:py-3 font-medium">
                <div className="flex flex-col gap-0.5">
                    <span className="text-[12px] md:text-[14px] font-bold text-white tracking-tight">
                        {portfolio.name}
                    </span>
                    <div className="flex items-center gap-1.5 text-[9px] md:text-[11px] font-mono text-white/40">
                        <span className="flex items-center gap-1">
                            <span
                                className={`h-1.5 w-1.5 md:h-2 md:w-2 rounded-full ${
                                    portfolio.isActive ? 'bg-emerald-400' : 'bg-slate-400'
                                }`}
                            />
                            {portfolio.isActive ? 'Active' : 'Inactive'}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                            <span
                                className={`h-1.5 w-1.5 md:h-2 md:w-2 rounded-full ${
                                    portfolio.isAutoResearch ? 'bg-purple-400' : 'bg-slate-400'
                                }`}
                            />
                            {portfolio.isAutoResearch ? 'Auto-Res' : 'Manual'}
                        </span>
                    </div>
                </div>
            </td>
            <td className="px-3 py-2 md:px-4 md:py-3 text-right font-mono text-[12px] md:text-[14px] font-medium text-white/95 align-middle">
                {formatMoney(portfolio.totalEquity)}
            </td>
            <td className="px-3 py-2 md:px-4 md:py-3 text-right font-mono text-[12px] md:text-[14px] align-middle">
                <div className="flex flex-col items-end gap-0.5">
                    <span
                        className={`font-bold ${
                            portfolio.todayPct >= 0 ? 'text-emerald-400' : 'text-red-400'
                        }`}
                    >
                        {portfolio.todayPct > 0 ? '+' : ''}
                        {portfolio.todayPct}%
                    </span>
                    <span
                        className={`text-[9px] md:text-[11px] ${
                            portfolio.weekPct >= 0 ? 'text-emerald-500/80' : 'text-red-400/80'
                        }`}
                    >
                        {portfolio.weekPct > 0 ? '+' : ''}
                        {portfolio.weekPct}% wk
                    </span>
                </div>
            </td>
        </tr>
    );
}

function SentimentHeader({ feeling }: { feeling: HomePageData['feeling'] }) {
    const isBullish = feeling.sentiment === 'BULLISH';
    const isBearish = feeling.sentiment === 'BEARISH';
    const sentimentColor = isBullish
        ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
        : isBearish
          ? 'bg-red-400 shadow-[0_0_8px_#f87171]'
          : 'bg-[#00f2fe] shadow-[0_0_8px_#00f2fe]';

    return (
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
                <span className="text-lg md:text-xl font-bold bg-gradient-to-r from-white via-slate-200 to-[#f6e05e] bg-clip-text text-transparent">
                    Live Overview
                </span>
                <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2 py-0.5 md:px-2.5 md:py-1 text-[10px] md:text-[11px] font-medium text-white shadow-inner">
                    <span
                        className={`mr-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${sentimentColor}`}
                    />
                    {feeling.sentimentEmoji && (
                        <span className="mr-1">{feeling.sentimentEmoji}</span>
                    )}
                    {feeling.sentiment}
                </div>
            </div>
            {feeling.sentimentLabel && (
                <span className="text-[11px] md:text-[12px] font-semibold text-slate-300 tracking-wide">
                    {feeling.sentimentLabel}
                </span>
            )}
        </div>
    );
}

function SPInlineRow({ benchmark }: { benchmark: HomePageData['benchmark'] }) {
    const spToday = benchmark.todayPct;
    const spWeek = benchmark.weekPct;

    return (
        <div className="flex items-center justify-between bg-yellow-900/10 border border-yellow-500/25 rounded-xl px-3 py-1.5 md:px-4 md:py-2 text-xs md:text-sm">
            <span className="font-bold text-yellow-300/90 tracking-tight text-[11px] md:text-[12px] uppercase">
                S&P 500 Benchmark
            </span>
            <div className="flex gap-2.5 md:gap-4 text-[11px] md:text-[12px] font-mono">
                <div>
                    <span className="text-white/40 mr-1">Today</span>
                    <span
                        className={
                            spToday >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'
                        }
                    >
                        {spToday > 0 ? '+' : ''}
                        {spToday}%
                    </span>
                </div>
                <span className="text-white/20">|</span>
                <div>
                    <span className="text-white/40 mr-1">Week</span>
                    <span
                        className={
                            spWeek >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'
                        }
                    >
                        {spWeek > 0 ? '+' : ''}
                        {spWeek}%
                    </span>
                </div>
            </div>
        </div>
    );
}

function FeelingDetail({ feeling }: { feeling: HomePageData['feeling'] }) {
    return (
        <div className="mt-2.5 space-y-3 md:space-y-4 animate-scale-in">
            <p className="text-xs md:text-sm leading-relaxed text-white/80 font-light italic bg-white/5 p-2 md:p-3 rounded-lg border border-white/5">
                &quot;{feeling.summary}&quot;
            </p>

            {feeling.confidence !== undefined && (
                <ConfidenceBar
                    label="Confidence"
                    value={feeling.confidence}
                    colorScheme={
                        feeling.confidence >= 70
                            ? 'success'
                            : feeling.confidence >= 40
                              ? 'warning'
                              : 'danger'
                    }
                    textStyle="hero"
                    className="bg-white/5 border border-white/10 p-2 md:p-3 rounded-xl text-[11px] md:text-[12px]"
                />
            )}

            {/* Concerns */}
            <div className="flex flex-col md:flex-row gap-2 md:gap-4">
                {feeling.primaryConcern && (
                    <div className="space-y-1 flex-1">
                        <span className="block text-[9px] md:text-[10px] text-white/40 uppercase tracking-widest font-black">
                            Primary Concern
                        </span>
                        <div className="inline-flex w-full rounded-lg border border-rose-500/20 bg-rose-500/10 px-2 py-1 md:px-2.5 md:py-1.5 text-[11px] md:text-[12px] text-rose-300 font-medium leading-tight">
                            ⚠️ {feeling.primaryConcern}
                        </div>
                    </div>
                )}
                {feeling.secondaryConcern && (
                    <div className="space-y-1 flex-1">
                        <span className="block text-[9px] md:text-[10px] text-white/40 uppercase tracking-widest font-black">
                            Secondary Concern
                        </span>
                        <div className="inline-flex w-full rounded-lg border border-white/10 bg-white/5 px-2 py-1 md:px-2.5 md:py-1.5 text-[11px] md:text-[12px] text-white/70 font-medium leading-tight">
                            🔍 {feeling.secondaryConcern}
                        </div>
                    </div>
                )}
            </div>

            {/* Meta footer */}
            <div className="flex flex-wrap items-center gap-1.5 border-t border-white/5 pt-2 text-[9px] md:text-[11px] text-white/40 font-mono">
                {feeling.lastAnalyzed && <span>Last: {feeling.lastAnalyzed}</span>}
                {feeling.modelUsed && <span>• Model: {feeling.modelUsed}</span>}
            </div>
        </div>
    );
}

function FeelingCollapsible({
    feeling,
    benchmark,
}: {
    feeling: HomePageData['feeling'];
    benchmark: HomePageData['benchmark'];
}) {
    const [isFeelingExpanded, setIsFeelingExpanded] = useState(false);

    return (
        <div className="flex flex-col gap-4">
            {/* Header Row */}
            <div className="flex flex-col gap-2 border-b border-white/10 pb-3">
                <SentimentHeader feeling={feeling} />
                <SPInlineRow benchmark={benchmark} />
            </div>

            {/* Collapsible Market Feeling */}
            <div className="border-b border-white/10 pb-3">
                <button
                    type="button"
                    onClick={() => setIsFeelingExpanded(!isFeelingExpanded)}
                    className="flex w-full items-center justify-between text-left text-xs md:text-sm font-semibold text-sky-400 hover:text-sky-300 focus:outline-none transition-colors duration-200 cursor-pointer"
                >
                    <span>🧠 Market Feeling Analysis</span>
                    <span className="text-[9px] md:text-[10px] font-mono bg-sky-950/40 px-1.5 py-0.5 md:px-2 md:py-1 rounded border border-sky-500/30 text-sky-300">
                        {isFeelingExpanded ? 'Collapse ▲' : 'Expand Details ▼'}
                    </span>
                </button>

                {/* Quick Preview when Collapsed */}
                {!isFeelingExpanded && (
                    <div className="mt-1.5 text-xs md:text-sm text-white/60 italic truncate">
                        &quot;{feeling.summary}&quot;
                    </div>
                )}

                {/* Full Details when Expanded */}
                {isFeelingExpanded && <FeelingDetail feeling={feeling} />}
            </div>
        </div>
    );
}

function BarometerSection({ barometer }: { barometer: MarketBarometer }) {
    const metrics = [
        {
            label: 'Trailing P/E',
            value: barometer.pe_ratio,
            format: (v: number) => v.toFixed(2),
            highlight: true,
        },
        {
            label: 'Forward P/E',
            value: barometer.forward_pe,
            format: (v: number) => v.toFixed(2),
            highlight: true,
        },
        { label: 'Price-to-Book', value: barometer.pb_ratio, format: (v: number) => v.toFixed(2) },
        { label: 'Price-to-Sales', value: barometer.ps_ratio, format: (v: number) => v.toFixed(2) },
    ];

    const beatRate = barometer.earnings_surprise_momentum;

    return (
        <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <h2 className="text-[10px] md:text-[11px] font-black uppercase tracking-widest text-white/40">
                    MARKET HEALTH BAROMETER (S&P 500)
                </h2>
                <span className="text-[9px] md:text-[10px] font-mono text-white/40">
                    As of {barometer.date}
                </span>
            </div>

            {/* Premium Glass Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {metrics.map((m) => {
                    const hasValue = m.value !== null && m.value !== undefined;
                    return (
                        <div
                            key={m.label}
                            className={`relative overflow-hidden rounded-xl border border-white/10 p-3 bg-white/5 backdrop-blur-[8px] transition-all duration-200 hover:border-white/20 flex flex-col justify-between ${
                                m.highlight
                                    ? 'bg-gradient-to-br from-white/[0.08] to-transparent'
                                    : ''
                            }`}
                        >
                            <span className="text-[10px] font-bold text-white/40 uppercase tracking-wide block mb-1">
                                {m.label}
                            </span>
                            <span className="text-xl md:text-2xl font-black text-white font-mono tracking-tight">
                                {hasValue ? m.format(Number(m.value)) : '—'}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* Beat Rate Gauge/Progress bar */}
            {beatRate !== null && beatRate !== undefined && (
                <div className="rounded-xl border border-white/10 p-3 bg-white/5 backdrop-blur-[8px] space-y-1.5 bg-gradient-to-r from-emerald-500/[0.03] to-transparent">
                    <div className="flex justify-between items-center text-[10px] md:text-[11px] font-bold">
                        <span className="text-white/40 uppercase tracking-wide">
                            Earnings Beat Rate
                        </span>
                        <span className="text-emerald-400 font-mono font-black">
                            {Number(beatRate).toFixed(1)}%
                        </span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden relative border border-white/5">
                        <div
                            className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)] transition-all duration-500"
                            style={{ width: `${beatRate}%` }}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

function Dashboard({ data }: { data: HomePageData }) {
    return (
        <div
            data-testid="dashboard"
            className="w-full border-y md:border border-white/10 md:rounded-2xl bg-glass-dark/40 backdrop-blur-[24px] shadow-[0_4px_15px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.1)] px-4 py-4 md:px-8 md:py-8 space-y-4 md:space-y-6"
        >
            <FeelingCollapsible feeling={data.feeling} benchmark={data.benchmark} />

            {data.barometer && <BarometerSection barometer={data.barometer} />}

            {/* Models Table Section */}
            <div className="space-y-2 md:space-y-3">
                <h2 className="text-[10px] md:text-[11px] font-black uppercase tracking-widest text-white/40">
                    Active Agent Portfolios
                </h2>
                <div className="overflow-hidden border border-white/10 rounded-xl bg-glass-dark/30 shadow-[0_4px_15px_rgba(0,0,0,0.5)]">
                    <table className="w-full border-collapse text-left text-xs md:text-sm">
                        <thead>
                            <tr className="border-b border-white/10 bg-white/5 font-bold text-white/60">
                                <th className="px-3 py-2 md:px-4 md:py-3 text-[10px] md:text-[11px] uppercase tracking-wider">
                                    Model
                                </th>
                                <th className="px-3 py-2 md:px-4 md:py-3 text-right text-[10px] md:text-[11px] uppercase tracking-wider">
                                    Equity
                                </th>
                                <th className="px-3 py-2 md:px-4 md:py-3 text-right text-[10px] md:text-[11px] uppercase tracking-wider">
                                    Today / Wk
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {data.portfolios.map((portfolio) => (
                                <PortfolioRow key={portfolio.name} portfolio={portfolio} />
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export function HomePage({ data }: { data: HomePageData }) {
    return (
        <div className="relative min-h-screen w-full text-white overflow-x-hidden">
            <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-2xl md:max-w-4xl flex-col items-center justify-start px-0 py-8 md:py-12">
                <header className="mb-6 md:mb-8 flex-shrink-0 w-full text-center px-4">
                    <h1 className="bg-gradient-to-r from-white via-yellow-100 to-[#f6e05e] bg-clip-text text-3xl md:text-4xl font-bold tracking-tight text-transparent drop-shadow-lg">
                        Market Overview
                    </h1>
                </header>

                <Dashboard data={data} />
            </div>
        </div>
    );
}
