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

export function HomePage({ data }: { data: HomePageData }) {
    // A helper to format currency safely
    const formatMoney = (val: number) => {
        const sign = val < 0 ? '-' : '';
        return `${sign}$${Math.abs(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    return (
        <div className="homepage-wrapper relative min-h-screen w-full bg-[#050914] text-white overflow-x-hidden">
            {/* 1. Modern Dot Grid Background with Subtle Ambient Glow */}
            <div className="absolute inset-0 z-0">
                {/* Ambient glowing orbs for depth */}
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(0,242,254,0.1),_transparent_40%)]" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,_rgba(74,222,128,0.07),_transparent_40%)]" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(246,224,94,0.05),_transparent_50%)]" />

                {/* Precise dot grid pattern */}
                <div
                    className="absolute inset-0 opacity-40"
                    style={{
                        backgroundImage:
                            'radial-gradient(rgba(255, 255, 255, 0.4) 1px, transparent 1px)',
                        backgroundSize: '24px 24px',
                    }}
                />
            </div>

            {/* Content Layer: Centered Unified Grid */}
            <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1600px] flex-col items-center justify-start px-4 py-8 sm:px-6 lg:px-8">
                <header className="mb-6 flex-shrink-0 w-full text-center">
                    <h1 className="bg-gradient-to-r from-white via-yellow-100 to-[#f6e05e] bg-clip-text text-3xl font-bold tracking-tight text-transparent drop-shadow-lg md:text-4xl">
                        Market Overview
                    </h1>
                </header>

                {/* Main Grid: S&P + Portfolios perfectly centered */}
                <div className="flex flex-wrap items-start justify-center gap-4 mb-5 w-full max-w-[1300px]">
                    {/* S&P 500 Benchmark Card - Formatted identically to portfolio cards but visually distinct */}
                    <div className="group relative flex w-[240px] flex-col overflow-hidden rounded-[12px] border border-yellow-500/40 bg-yellow-900/20 p-3 shadow-[0_0_15px_rgba(234,179,8,0.15),inset_0_1px_1px_rgba(255,255,255,0.2)] backdrop-blur-[24px]">
                        <div className="mb-3 flex items-center justify-between text-xs text-white/50">
                            <div className="flex flex-wrap gap-1.5">
                                <span className="flex items-center gap-1 rounded bg-yellow-500/20 px-1.5 py-0.5 text-[10px] font-medium text-yellow-300 border border-yellow-500/30">
                                    GLOBAL BENCHMARK
                                </span>
                            </div>
                        </div>
                        <h2 className="mb-3 truncate bg-gradient-to-r from-white to-[#f6e05e] bg-clip-text text-lg font-bold tracking-tight text-transparent drop-shadow-sm">
                            S&P 500
                        </h2>

                        <div className="flex items-end justify-between border-t border-yellow-500/20 pt-2 mt-1">
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
                    </div>

                    {/* Individual Portfolio Cards */}
                    {data.portfolios.map((portfolio) => (
                        <div
                            key={portfolio.name}
                            className="group relative flex w-[240px] flex-col overflow-hidden rounded-[12px] border border-white/10 bg-[#1a1e23]/50 p-3 shadow-[0_4px_15px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.1)] backdrop-blur-[24px] transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-[#1a1e23]/70"
                        >
                            <div className="mb-3 flex items-center justify-between text-xs text-white/50">
                                <div className="flex flex-wrap gap-1.5">
                                    {portfolio.isActive && (
                                        <span className="flex items-center gap-1 rounded bg-white/5 px-1.5 py-0.5 text-[10px] font-medium text-white/70 border border-white/10">
                                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />{' '}
                                            Active
                                        </span>
                                    )}
                                    <span className="flex items-center gap-1 rounded bg-white/5 px-1.5 py-0.5 text-[10px] font-medium text-white/70 border border-white/10">
                                        <span
                                            className={`h-1.5 w-1.5 rounded-full ${portfolio.isAutoResearch ? 'bg-[#00f2fe]' : 'bg-white/20'}`}
                                        />
                                        Auto-Research
                                    </span>
                                </div>
                            </div>
                            <h2 className="mb-3 truncate bg-gradient-to-r from-white to-[#00f2fe] bg-clip-text text-lg font-bold tracking-tight text-transparent drop-shadow-sm">
                                {portfolio.name}
                            </h2>

                            <div className="flex items-end justify-between border-t border-white/10 pt-2 mt-1">
                                <div>
                                    <span className="block text-[10px] text-white/50">Equity</span>
                                    <span className="text-base font-medium tracking-tight text-white">
                                        {formatMoney(portfolio.totalEquity)}
                                    </span>
                                </div>
                                <div className="text-right">
                                    <span className="block text-[10px] text-white/50">Today</span>
                                    <span
                                        className={`text-sm font-medium tracking-tight ${portfolio.todayPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                                    >
                                        {portfolio.todayPct > 0 ? '+' : ''}
                                        {portfolio.todayPct}%
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Footer Section: Market Feeling spans horizontally below the grid */}
                <div className="w-full max-w-[1000px] overflow-hidden rounded-[12px] border border-white/10 bg-[#1a1e23]/50 p-4 shadow-[0_4px_15px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.1)] backdrop-blur-[24px]">
                    <div className="flex items-center justify-between border-b border-white/10 pb-2.5 mb-2.5">
                        <div className="flex items-center">
                            <h2 className="mr-3 bg-gradient-to-r from-white to-[#0575e6] bg-clip-text text-base font-bold tracking-tight text-transparent">
                                Market Feeling
                            </h2>
                            <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-white shadow-inner">
                                <span
                                    className={`mr-1.5 h-1.5 w-1.5 rounded-full ${data.feeling.sentiment === 'BULLISH' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : data.feeling.sentiment === 'BEARISH' ? 'bg-red-400 shadow-[0_0_8px_#f87171]' : 'bg-[#00f2fe] shadow-[0_0_8px_#00f2fe]'}`}
                                />
                                {data.feeling.sentiment.toUpperCase()}
                            </div>
                        </div>
                    </div>
                    <p className="text-sm leading-relaxed text-white/80">{data.feeling.summary}</p>
                </div>
            </div>
        </div>
    );
}
