import type { MarketFeeling, Trade } from '@llm-market-bench/database';
import { Badge, Card, ConfidenceBar, SectionHeading } from '@llm-market-bench/ui-design-system';

interface AIFeelingCardProps {
    marketFeeling: (MarketFeeling & { formattedTime?: string }) | null;
    trades: (Trade & { portfolios: { owner_id: string }; formattedTime: string })[];
    isSentimentStale: boolean;
}

type ColorScheme = 'accent' | 'success' | 'danger' | 'info' | 'warning';

function getDirectionColor(direction: string | null | undefined): string {
    if (direction?.toUpperCase() === 'BULLISH') return 'text-neon-green-500';
    if (direction?.toUpperCase() === 'BEARISH') return 'text-alert-red-500';
    return 'text-zinc-400';
}

function getDirectionColorScheme(direction: string | null | undefined): ColorScheme {
    if (direction === 'BULLISH') return 'success';
    if (direction === 'BEARISH') return 'danger';
    return 'accent';
}

function getConfidenceColorScheme(score: number | null | undefined): ColorScheme {
    if (!score) return 'accent';
    if (score >= 70) return 'success';
    if (score >= 40) return 'warning';
    return 'danger';
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function SentimentHeader({
    emoji,
    label,
    direction,
    isStale,
    hasFeeling,
}: {
    emoji: string;
    label: string;
    direction: string | null;
    isStale: boolean;
    hasFeeling: boolean;
}) {
    return (
        <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3 flex-wrap">
                <span className="text-4xl animate-float">{emoji}</span>
                <div>
                    <p className="text-[10px] font-black text-zinc-400 uppercase tracking-widest mb-1">
                        Market Sentiment
                    </p>
                    <div
                        className={`text-3xl font-black text-display leading-none ${getDirectionColor(direction)}`}
                    >
                        {label}
                    </div>
                </div>
            </div>

            <div className="flex flex-col items-end gap-2 shrink-0">
                {direction && (
                    <Badge
                        variant="soft"
                        colorScheme={getDirectionColorScheme(direction)}
                        size="sm"
                    >
                        {direction}
                    </Badge>
                )}
                {isStale && hasFeeling && (
                    <span
                        className="text-[9px] px-2 py-0.5 bg-amber-500/15 text-amber-500 rounded-full font-bold border border-amber-500/20"
                        title="Data is older than 4 hours"
                    >
                        ⚠ STALE
                    </span>
                )}
            </div>
        </div>
    );
}

function TradeSplit({ buyCount, sellCount }: { buyCount: number; sellCount: number }) {
    return (
        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <div className="flex flex-col items-center p-3 rounded-xl bg-neon-green-50/60 dark:bg-neon-green-950/20 border border-neon-green-200/60 dark:border-neon-green-900/40 hover:bg-neon-green-50 dark:hover:bg-neon-green-950/30 transition-colors duration-200">
                <span className="text-2xl font-black text-neon-green-500">{buyCount}</span>
                <span className="text-[9px] font-black text-neon-green-600 dark:text-neon-green-400 uppercase tracking-widest mt-0.5">
                    Buys
                </span>
            </div>
            <div className="flex flex-col items-center p-3 rounded-xl bg-alert-red-50/60 dark:bg-alert-red-950/20 border border-alert-red-200/60 dark:border-alert-red-900/40 hover:bg-alert-red-50 dark:hover:bg-alert-red-950/30 transition-colors duration-200">
                <span className="text-2xl font-black text-alert-red-500">{sellCount}</span>
                <span className="text-[9px] font-black text-alert-red-600 dark:text-alert-red-400 uppercase tracking-widest mt-0.5">
                    Sells
                </span>
            </div>
        </div>
    );
}

function CardFooter({
    formattedTime,
    modelUsed,
}: {
    formattedTime?: string;
    modelUsed?: string | null;
}) {
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between pt-2 border-t border-zinc-100 dark:border-zinc-800">
                <span className="text-[10px] text-zinc-400 font-mono tabular-nums">
                    {formattedTime ? `Last analyzed: ${formattedTime}` : 'Waiting for analysis...'}
                </span>
                {modelUsed && (
                    <span className="text-[10px] text-zinc-400 font-mono">{modelUsed}</span>
                )}
            </div>
            <a
                href="/market-overview"
                className="inline-flex items-center gap-1 text-xs text-electric-blue-500 hover:text-electric-blue-700 dark:hover:text-electric-blue-300 transition-colors font-semibold underline underline-offset-2"
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
                    <title>Arrow right</title>
                    <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
            </a>
        </div>
    );
}

// ── Main export ────────────────────────────────────────────────────────────────

export function AIFeelingCard({ marketFeeling, trades, isSentimentStale }: AIFeelingCardProps) {
    const sentiment = {
        label: marketFeeling?.sentiment_label || 'Analyzing...',
        emoji: marketFeeling?.sentiment_emoji || '🤔',
        direction: marketFeeling?.market_direction || null,
        confidence: marketFeeling?.confidence_score || null,
        why: marketFeeling?.why_explanation || null,
        primaryConcern: marketFeeling?.primary_concern || null,
    };

    const buyCount = trades.filter((t) => t.signal === 'BUY').length;
    const sellCount = trades.filter((t) => t.signal === 'SELL').length;
    const totalTrades = trades.length;

    return (
        <section className="space-y-8 animate-slide-up">
            <SectionHeading gradient="electric">How is the AI Feeling?</SectionHeading>

            <Card
                isHoverable
                padding="lg"
                className="relative overflow-hidden border border-zinc-200 dark:border-zinc-800 hover:border-electric-blue-300 dark:hover:border-electric-blue-700 hover:shadow-electric-blue-500/10 transition-all duration-300"
            >
                {/* Subtle gradient background accent */}
                <div className="absolute inset-0 bg-gradient-to-br from-electric-blue-50/40 via-transparent to-deep-purple-50/20 dark:from-electric-blue-950/20 dark:via-transparent dark:to-deep-purple-950/10 pointer-events-none rounded-[inherit]" />

                <div className="relative space-y-5">
                    <SentimentHeader
                        emoji={sentiment.emoji}
                        label={sentiment.label}
                        direction={sentiment.direction}
                        isStale={isSentimentStale}
                        hasFeeling={!!marketFeeling}
                    />

                    {sentiment.confidence !== null && (
                        <ConfidenceBar
                            label="Confidence"
                            value={sentiment.confidence}
                            colorScheme={getConfidenceColorScheme(sentiment.confidence)}
                            textStyle="default"
                            className="w-full"
                        />
                    )}

                    {sentiment.why && (
                        <p className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed italic border-l-2 border-electric-blue-300 dark:border-electric-blue-700 pl-3">
                            "{sentiment.why}"
                        </p>
                    )}

                    {sentiment.primaryConcern && (
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-bold">
                                Primary Concern:
                            </span>
                            <span className="text-xs px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 font-medium">
                                {sentiment.primaryConcern}
                            </span>
                        </div>
                    )}

                    {totalTrades > 0 && <TradeSplit buyCount={buyCount} sellCount={sellCount} />}

                    <CardFooter
                        formattedTime={marketFeeling?.formattedTime}
                        modelUsed={marketFeeling?.model_used}
                    />
                </div>
            </Card>
        </section>
    );
}
