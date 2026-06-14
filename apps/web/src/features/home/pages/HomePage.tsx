import { Badge, Card } from '@llm-market-bench/ui-design-system';

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
    feeling: { sentiment: string; summary: string };
}

/** Maps today's return % to design system card metadata. */
function getPerformanceMeta(todayPct: number): {
    colorScheme: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
    titleGradient: string;
} {
    if (todayPct >= 2) {
        // Strong positive — gold
        return {
            colorScheme: 'warning',
            titleGradient: 'from-amber-100 to-[#f59e0b]',
        };
    }
    if (todayPct >= 0.25) {
        // Mild positive — emerald
        return {
            colorScheme: 'success',
            titleGradient: 'from-emerald-100 to-[#34d399]',
        };
    }
    if (todayPct >= -0.25) {
        // Flat / neutral — sky blue
        return {
            colorScheme: 'neutral',
            titleGradient: 'from-sky-100 to-[#38bdf8]',
        };
    }
    if (todayPct >= -2) {
        // Mild negative — rose
        return {
            colorScheme: 'info',
            titleGradient: 'from-rose-100 to-[#f43f5e]',
        };
    }
    // Strong negative — deep crimson
    return {
        colorScheme: 'danger',
        titleGradient: 'from-red-200 to-[#dc2626]',
    };
}

export function HomePage({ data }: { data: HomePageData }) {
    // A helper to format currency safely
    const formatMoney = (val: number) => {
        const sign = val < 0 ? '-' : '';
        return `${sign}$${Math.abs(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    return (
        <div className="homepage-wrapper relative min-h-screen w-full text-white overflow-x-hidden">
            {/* Content Layer: Centered Unified Grid */}
            <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1600px] flex-col items-center justify-start px-4 py-8 sm:px-6 lg:px-8">
                <header className="mb-6 flex-shrink-0 w-full text-center relative">
                    <h1 className="bg-gradient-to-r from-white via-yellow-100 to-[#f6e05e] bg-clip-text text-3xl font-bold tracking-tight text-transparent drop-shadow-lg md:text-4xl">
                        Market Overview
                    </h1>
                </header>

                {/* Main Grid: S&P + Portfolios perfectly centered */}
                <div className="flex flex-wrap items-stretch justify-center gap-4 mb-5 w-full max-w-[1300px]">
                    {/* S&P 500 Benchmark Card - Formatted identically to portfolio cards but visually distinct */}
                    <Card
                        variant="glass-warning"
                        className="w-[240px] flex flex-col overflow-hidden p-3"
                        radius="xl"
                        padding="none"
                    >
                        <div className="mb-3 flex items-center justify-between text-xs text-white/50">
                            <div className="flex flex-wrap gap-1.5">
                                <Badge variant="glass" colorScheme="warning" size="sm" radius="md">
                                    GLOBAL BENCHMARK
                                </Badge>
                            </div>
                        </div>
                        {/* overflow-hidden wrapper prevents the truncate+gradient-text invisible-ellipsis bug */}
                        <div className="mb-3 overflow-hidden w-full">
                            <h2 className="whitespace-nowrap bg-gradient-to-r from-white to-[#f6e05e] bg-clip-text text-lg font-bold tracking-tight text-transparent drop-shadow-sm">
                                S&P 500
                            </h2>
                        </div>

                        <div className="mt-auto flex items-end justify-between border-t border-yellow-500/20 pt-2">
                            <div>
                                <span className="block text-[10px] text-white/50">This Week</span>
                                <span
                                    className={`text-sm font-medium tracking-tight ${data.benchmark.weekPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                                >
                                    {data.benchmark.weekPct > 0 ? '+' : ''}
                                    {data.benchmark.weekPct}%
                                </span>
                            </div>
                            <div className="text-right">
                                <span className="block text-[10px] text-white/50">Today</span>
                                <span
                                    className={`text-sm font-medium tracking-tight ${data.benchmark.todayPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                                >
                                    {data.benchmark.todayPct > 0 ? '+' : ''}
                                    {data.benchmark.todayPct}%
                                </span>
                            </div>
                        </div>
                    </Card>

                    {/* Individual Portfolio Cards — heatmap-coloured by today's return */}
                    {data.portfolios.map((portfolio) => {
                        const perfMeta = getPerformanceMeta(portfolio.todayPct);
                        return (
                            <Card
                                key={portfolio.name}
                                variant="glass"
                                colorScheme={perfMeta.colorScheme}
                                isHoverable
                                className="w-[240px] flex flex-col overflow-hidden p-3"
                                radius="xl"
                                padding="none"
                            >
                                <div className="mb-3 flex items-center justify-between text-xs text-white/50">
                                    <div className="flex flex-wrap gap-1.5">
                                        {portfolio.isActive && (
                                            <Badge
                                                variant="glass"
                                                colorScheme="success"
                                                size="sm"
                                                radius="md"
                                                showDot
                                            >
                                                Active
                                            </Badge>
                                        )}
                                        <Badge
                                            variant="glass"
                                            colorScheme={
                                                portfolio.isAutoResearch ? 'info' : 'neutral'
                                            }
                                            size="sm"
                                            radius="md"
                                            showDot
                                        >
                                            Auto-Research
                                        </Badge>
                                    </div>
                                </div>
                                {/* overflow-hidden wrapper fixes truncate+gradient-text invisible-ellipsis bug */}
                                <div className="mb-3 overflow-hidden w-full">
                                    <h2
                                        className={`whitespace-nowrap bg-gradient-to-r ${perfMeta.titleGradient} bg-clip-text text-lg font-bold tracking-tight text-transparent drop-shadow-sm`}
                                    >
                                        {portfolio.name}
                                    </h2>
                                </div>

                                <div className="mt-auto flex items-end justify-between border-t border-white/10 pt-2">
                                    <div>
                                        <span className="block text-[10px] text-white/50">
                                            Equity
                                        </span>
                                        <span className="text-base font-medium tracking-tight text-white">
                                            {formatMoney(portfolio.totalEquity)}
                                        </span>
                                    </div>
                                    <div className="text-right">
                                        <span className="block text-[10px] text-white/50">
                                            Today
                                        </span>
                                        <span
                                            className={`text-sm font-medium tracking-tight ${portfolio.todayPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                                        >
                                            {portfolio.todayPct > 0 ? '+' : ''}
                                            {portfolio.todayPct}%
                                        </span>
                                    </div>
                                </div>
                            </Card>
                        );
                    })}
                </div>

                {/* Footer Section: Market Feeling spans horizontally below the grid */}
                <Card
                    variant="glass"
                    className="w-full max-w-[1000px] overflow-hidden p-4"
                    radius="xl"
                    padding="none"
                >
                    <div className="mb-2.5 flex items-center justify-between border-b border-white/10 pb-2.5">
                        <div className="flex items-center">
                            <h2 className="mr-3 bg-gradient-to-r from-white to-[#0575e6] bg-clip-text text-base font-bold tracking-tight text-transparent">
                                Market Feeling
                            </h2>
                            <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-white shadow-inner">
                                <span
                                    className={`mr-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${data.feeling.sentiment === 'BULLISH' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : data.feeling.sentiment === 'BEARISH' ? 'bg-red-400 shadow-[0_0_8px_#f87171]' : 'bg-[#00f2fe] shadow-[0_0_8px_#00f2fe]'}`}
                                />
                                {data.feeling.sentiment.toUpperCase()}
                            </div>
                        </div>
                    </div>
                    <p className="text-sm leading-relaxed text-white/80">{data.feeling.summary}</p>
                </Card>
            </div>
        </div>
    );
}
