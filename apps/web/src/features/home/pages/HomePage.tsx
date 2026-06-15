import { Badge, Card, ConfidenceBar } from '@llm-market-bench/ui-design-system';

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

interface PortfolioCardProps {
    portfolio: HomePageData['portfolios'][number];
}

function PortfolioCard({ portfolio }: PortfolioCardProps) {
    const perfMeta = getPerformanceMeta(portfolio.todayPct);
    const formatMoney = (val: number) => {
        const sign = val < 0 ? '-' : '';
        return `${sign}$${Math.abs(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    return (
        <Card
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
                        <Badge variant="glass" colorScheme="success" size="sm" radius="md" showDot>
                            Active
                        </Badge>
                    )}
                    <Badge
                        variant="glass"
                        colorScheme={portfolio.isAutoResearch ? 'info' : 'neutral'}
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
        </Card>
    );
}

interface BenchmarkCardProps {
    benchmark: HomePageData['benchmark'];
}

function BenchmarkCard({ benchmark }: BenchmarkCardProps) {
    return (
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
            <div className="mb-3 overflow-hidden w-full">
                <h2 className="whitespace-nowrap bg-gradient-to-r from-white to-[#f6e05e] bg-clip-text text-lg font-bold tracking-tight text-transparent drop-shadow-sm">
                    S&P 500
                </h2>
            </div>

            <div className="mt-auto flex items-end justify-between border-t border-yellow-500/20 pt-2">
                <div>
                    <span className="block text-[10px] text-white/50">This Week</span>
                    <span
                        className={`text-sm font-medium tracking-tight ${benchmark.weekPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                    >
                        {benchmark.weekPct > 0 ? '+' : ''}
                        {benchmark.weekPct}%
                    </span>
                </div>
                <div className="text-right">
                    <span className="block text-[10px] text-white/50">Today</span>
                    <span
                        className={`text-sm font-medium tracking-tight ${benchmark.todayPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                    >
                        {benchmark.todayPct > 0 ? '+' : ''}
                        {benchmark.todayPct}%
                    </span>
                </div>
            </div>
        </Card>
    );
}

interface ConcernsSectionProps {
    primaryConcern?: string;
    secondaryConcern?: string;
}

function ConcernsSection({ primaryConcern, secondaryConcern }: ConcernsSectionProps) {
    if (!primaryConcern && !secondaryConcern) return null;
    return (
        <div className="md:col-span-1 flex flex-col justify-start gap-4">
            {primaryConcern && (
                <div className="space-y-1.5">
                    <span className="block text-[10px] text-white/40 uppercase tracking-widest font-black">
                        Primary Concern
                    </span>
                    <div className="inline-flex rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300 font-medium shadow-sm leading-snug">
                        ⚠️ {primaryConcern}
                    </div>
                </div>
            )}
            {secondaryConcern && (
                <div className="space-y-1.5">
                    <span className="block text-[10px] text-white/40 uppercase tracking-widest font-black">
                        Secondary Concern
                    </span>
                    <div className="inline-flex rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/70 font-medium leading-snug">
                        🔍 {secondaryConcern}
                    </div>
                </div>
            )}
        </div>
    );
}

interface MetadataFooterProps {
    modelUsed?: string;
    lastAnalyzed?: string;
}

function MetadataFooter({ modelUsed, lastAnalyzed }: MetadataFooterProps) {
    if (!modelUsed && !lastAnalyzed) return null;
    return (
        <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-white/10 pt-3 text-[10px] text-white/40 font-mono">
            {lastAnalyzed && <span>Last analyzed: {lastAnalyzed}</span>}
            {modelUsed && lastAnalyzed && <span>•</span>}
            {modelUsed && <span>Model: {modelUsed}</span>}
        </div>
    );
}

interface MarketFeelingCardProps {
    feeling: HomePageData['feeling'];
}

function MarketFeelingCard({ feeling }: MarketFeelingCardProps) {
    return (
        <Card
            variant="glass"
            className="w-full max-w-[1000px] overflow-hidden p-6"
            radius="xl"
            padding="none"
        >
            {/* Header */}
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                    <h2 className="bg-gradient-to-r from-white to-[#0575e6] bg-clip-text text-lg font-bold tracking-tight text-transparent">
                        Market Feeling
                    </h2>
                    <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-white shadow-inner">
                        <span
                            className={`mr-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${feeling.sentiment === 'BULLISH' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : feeling.sentiment === 'BEARISH' ? 'bg-red-400 shadow-[0_0_8px_#f87171]' : 'bg-[#00f2fe] shadow-[0_0_8px_#00f2fe]'}`}
                        />
                        {feeling.sentiment.toUpperCase()}
                    </div>
                </div>

                {/* Emoji & Label */}
                <div className="flex items-center gap-2">
                    {feeling.sentimentEmoji && (
                        <span className="text-2xl animate-float">{feeling.sentimentEmoji}</span>
                    )}
                    {feeling.sentimentLabel && (
                        <span className="text-sm font-bold text-white tracking-wide">
                            {feeling.sentimentLabel}
                        </span>
                    )}
                </div>
            </div>

            {/* Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Why explanation + Confidence Bar */}
                <div className="md:col-span-2 space-y-4">
                    <p className="text-sm leading-relaxed text-white/80 font-light italic">
                        "{feeling.summary}"
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
                            className="max-w-md bg-white/5 border border-white/10 p-2 rounded-xl"
                        />
                    )}
                </div>

                {/* Concerns Section */}
                <ConcernsSection
                    primaryConcern={feeling.primaryConcern}
                    secondaryConcern={feeling.secondaryConcern}
                />
            </div>

            {/* Footer Metadata */}
            <MetadataFooter modelUsed={feeling.modelUsed} lastAnalyzed={feeling.lastAnalyzed} />
        </Card>
    );
}

export function HomePage({ data }: { data: HomePageData }) {
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
                    <BenchmarkCard benchmark={data.benchmark} />

                    {data.portfolios.map((portfolio) => (
                        <PortfolioCard key={portfolio.name} portfolio={portfolio} />
                    ))}
                </div>

                <MarketFeelingCard feeling={data.feeling} />
            </div>
        </div>
    );
}
