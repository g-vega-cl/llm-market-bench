import type {
    Decision,
    MarketDataCache,
    MarketFeeling,
    Memory,
    NewsletterSnapshot,
    Trade,
} from '@llm-market-bench/database';
import { Badge, Card, ConfidenceBar, HeroBackground } from '@llm-market-bench/ui-design-system';

interface MarketStatusHeroProps {
    data: {
        trades?: Trade[];
        decisions?: Decision[];
        memories?: Memory[];
        priceUpdates?: MarketDataCache[];
        futureEvents?: Record<string, unknown>[];
        newsletters?: NewsletterSnapshot[];
        marketFeeling?: (MarketFeeling & { formattedTime?: string }) | null;
        serverTime?: string;
        isMarketOpen: boolean;
        isSentimentStale: boolean;
        todayDateString: string;
    };
}

function getDirectionColor(direction: string | null | undefined): string {
    switch (direction?.toUpperCase()) {
        case 'BULLISH':
            return 'text-neon-green-400';
        case 'BEARISH':
            return 'text-alert-red-400';
        default:
            return 'text-steel-400';
    }
}

function getConfidenceColorScheme(
    score: number | null | undefined,
): 'accent' | 'success' | 'danger' | 'info' | 'warning' {
    if (!score) return 'accent';
    if (score >= 70) return 'success';
    if (score >= 40) return 'warning';
    return 'danger';
}

export function MarketStatusHero({ data }: MarketStatusHeroProps) {
    const isMarketOpen = data.isMarketOpen;
    const isStale = data.isSentimentStale;

    const totalTrades = data.trades?.length || 0;
    const activeMemories = data.memories?.filter((m) => m.status === 'ACTIVE').length || 0;

    const marketFeeling = data.marketFeeling;

    const buyCount = data.trades?.filter((t) => t.signal === 'BUY').length || 0;
    const sellCount = data.trades?.filter((t) => t.signal === 'SELL').length || 0;

    const fallbackSentiment = {
        label: marketFeeling?.sentiment_label || 'Analyzing...',
        emoji: marketFeeling?.sentiment_emoji || '🤔',
        direction: marketFeeling?.market_direction || null,
        confidence: marketFeeling?.confidence_score || null,
        why: marketFeeling?.why_explanation || null,
        primaryConcern: marketFeeling?.primary_concern || null,
    };

    return (
        <HeroBackground gradient="electric">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
                <div className="lg:col-span-2 flex flex-col gap-6 animate-slide-up">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-4 flex-wrap">
                        <h1 className="text-lg font-bold text-white uppercase tracking-wider text-display drop-shadow-lg m-0">
                            TODAY
                        </h1>
                        <Badge variant="outline" colorScheme="neutral" radius="none">
                            {data.todayDateString}
                        </Badge>
                    </div>

                    <p className="text-xs font-normal text-electric-blue-100 leading-relaxed max-w-2xl drop-shadow m-0">
                        Six AI agents. One virtual market. Real-time benchmark of machine cognition
                        vs. the S&P 500.
                    </p>

                    <div className="flex flex-wrap gap-4 sm:gap-6 pt-2">
                        <StatBadge
                            icon="📰"
                            label="Newsletters"
                            value={data.newsletters?.length || 0}
                        />
                        <StatBadge icon="💼" label="Trades" value={totalTrades} />
                        <StatBadge icon="🧠" label="Active Memories" value={activeMemories} />
                    </div>
                </div>

                <div className="lg:col-span-1 flex flex-col gap-6 animate-slide-up animate-stagger-2">
                    <Card
                        variant="glass"
                        padding="md"
                        className="rounded-none shadow-sm flex flex-col gap-4"
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-electric-blue-200 uppercase tracking-wider">
                                Market Status
                            </span>
                            <Badge
                                variant="soft"
                                colorScheme={isMarketOpen ? 'success' : 'neutral'}
                                radius="none"
                                className="gap-2"
                            >
                                <span
                                    className={
                                        isMarketOpen
                                            ? 'live-dot'
                                            : 'w-2 h-2 rounded-none bg-steel-400'
                                    }
                                />
                                {isMarketOpen ? 'OPEN' : 'CLOSED'}
                            </Badge>
                        </div>

                        <div className="text-lg font-bold font-mono text-white text-display drop-shadow">
                            {isMarketOpen ? 'Trading Live' : 'After Hours'}
                        </div>
                        <p className="text-xs font-normal text-electric-blue-200 leading-relaxed">
                            {isMarketOpen
                                ? 'AI agents are actively analyzing and executing trades'
                                : 'Next session at 09:30 ET'}
                        </p>
                    </Card>

                    <Card
                        variant="glass"
                        padding="md"
                        className="rounded-none shadow-sm flex flex-col gap-4"
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-electric-blue-200 uppercase tracking-wider">
                                How I'm Feeling
                            </span>
                            <div className="flex items-center gap-2">
                                <span className="text-lg">{fallbackSentiment.emoji}</span>
                                {isStale && marketFeeling && (
                                    <span
                                        className="text-xs font-bold px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded-none"
                                        title="Data is older than 4 hours"
                                    >
                                        ⚠
                                    </span>
                                )}
                            </div>
                        </div>

                        <div
                            className={`text-lg font-bold font-mono text-display drop-shadow ${getDirectionColor(fallbackSentiment.direction)}`}
                        >
                            {fallbackSentiment.label}
                        </div>

                        {fallbackSentiment.direction && (
                            <div className="flex items-center gap-2">
                                <Badge
                                    variant="soft"
                                    colorScheme={
                                        fallbackSentiment.direction === 'BULLISH'
                                            ? 'success'
                                            : fallbackSentiment.direction === 'BEARISH'
                                              ? 'danger'
                                              : 'neutral'
                                    }
                                    size="sm"
                                    radius="none"
                                >
                                    {fallbackSentiment.direction}
                                </Badge>
                            </div>
                        )}

                        {fallbackSentiment.confidence !== null && (
                            <ConfidenceBar
                                label="Confidence"
                                value={fallbackSentiment.confidence}
                                colorScheme={getConfidenceColorScheme(fallbackSentiment.confidence)}
                                textStyle="hero"
                            />
                        )}

                        {fallbackSentiment.why && (
                            <p className="text-xs font-normal text-electric-blue-100 leading-relaxed italic">
                                "{fallbackSentiment.why}"
                            </p>
                        )}

                        {fallbackSentiment.primaryConcern && (
                            <div className="flex flex-wrap gap-2">
                                <span className="text-xs font-bold text-electric-blue-300 uppercase tracking-wider">
                                    Concern:
                                </span>
                                <span className="text-xs font-normal px-2 py-1 bg-white/5 rounded-none text-electric-blue-100 border border-white/10">
                                    {fallbackSentiment.primaryConcern}
                                </span>
                            </div>
                        )}

                        {totalTrades > 0 && (
                            <div className="flex gap-4 pt-4 border-t border-white/10">
                                <div className="flex-1 text-center p-3 rounded-none bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 transition-all duration-300 flex flex-col gap-1">
                                    <div className="text-lg font-bold font-mono text-neon-green-400 drop-shadow">
                                        {buyCount}
                                    </div>
                                    <div className="text-xs font-bold text-electric-blue-200 uppercase tracking-wider">
                                        Buys
                                    </div>
                                </div>
                                <div className="flex-1 text-center p-3 rounded-none bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 transition-all duration-300 flex flex-col gap-1">
                                    <div className="text-lg font-bold font-mono text-alert-red-400 drop-shadow">
                                        {sellCount}
                                    </div>
                                    <div className="text-xs font-bold text-electric-blue-200 uppercase tracking-wider">
                                        Sells
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="flex items-center gap-2 pt-3 border-t border-white/10">
                            <span className="text-xs font-normal text-electric-blue-300">
                                {marketFeeling?.formattedTime
                                    ? `Last analyzed: ${marketFeeling.formattedTime}`
                                    : 'Waiting for analysis...'}
                            </span>
                            {marketFeeling?.model_used && (
                                <span className="text-xs font-normal text-electric-blue-400/50">
                                    • {marketFeeling.model_used}
                                </span>
                            )}
                        </div>
                        <div className="pt-3 border-t border-white/10">
                            <a
                                href="/market-overview"
                                className="text-xs font-bold text-electric-blue-200 hover:text-white transition-colors flex items-center gap-1 underline underline-offset-2"
                            >
                                View full market analysis
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    width="12"
                                    height="12"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <title>SVG</title>
                                    <path d="M5 12h14M12 5l7 7-7 7" />
                                </svg>
                            </a>
                        </div>
                    </Card>
                </div>
            </div>
        </HeroBackground>
    );
}

function StatBadge({ icon, label, value }: { icon: string; label: string; value: number }) {
    return (
        <div className="group flex items-center gap-3 px-4 py-2.5 bg-white/10 backdrop-blur-sm rounded-none border border-white/20 transition-all duration-300 shadow-sm cursor-default">
            <span className="text-lg">{icon}</span>
            <div className="flex flex-col gap-0.5">
                <div className="text-lg font-bold font-mono text-white drop-shadow">{value}</div>
                <div className="text-xs font-bold text-electric-blue-200 uppercase tracking-wider">
                    {label}
                </div>
            </div>
        </div>
    );
}
