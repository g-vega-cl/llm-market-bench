import type { MarketFeeling, Trade } from '@llm-market-bench/database';
import { Badge, Card, ConfidenceBar, SectionHeading } from '@llm-market-bench/ui-design-system';
import { isSystemPortfolio } from '~/features/portfolios/lib/config';

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
            <div className="flex items-center gap-2.5 flex-wrap">
                <span className="text-xl">{emoji}</span>
                <div className="flex flex-col gap-0.5">
                    <p className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                        Market Sentiment
                    </p>
                    <div
                        className={`text-lg font-bold text-display leading-tight ${getDirectionColor(direction)}`}
                    >
                        {label}
                    </div>
                </div>
            </div>

            <div className="flex flex-col items-end gap-1.5 shrink-0">
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
                    <Badge colorScheme="warning" variant="outline" size="xs">
                        STALE
                    </Badge>
                )}
            </div>
        </div>
    );
}

function TradeSplit({ buyCount, sellCount }: { buyCount: number; sellCount: number }) {
    return (
        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-boxel-bevel-hi">
            <div className="voxel-trough rounded-none p-2.5 flex flex-col items-center gap-0.5">
                <span className="text-sm font-bold font-mono text-success">{buyCount}</span>
                <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                    Buys
                </span>
            </div>
            <div className="voxel-trough rounded-none p-2.5 flex flex-col items-center gap-0.5">
                <span className="text-sm font-bold font-mono text-danger">{sellCount}</span>
                <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
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
        <div className="space-y-2 mt-auto">
            <div className="flex items-center justify-between pt-2 border-t border-boxel-bevel-hi text-xs font-normal font-mono text-boxel-muted">
                <span>
                    {formattedTime ? `Last analyzed: ${formattedTime}` : 'Waiting for analysis...'}
                </span>
                {modelUsed && <span>{modelUsed}</span>}
            </div>
            <a
                href="/market-overview"
                className="inline-flex items-center gap-1 text-sm font-bold text-accent hover:underline uppercase tracking-wider"
            >
                View full market analysis →
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

    const llmTrades = trades.filter((t) => !isSystemPortfolio(t.portfolios?.owner_id));
    const buyCount = llmTrades.filter((t) => t.signal === 'BUY').length;
    const sellCount = llmTrades.filter((t) => t.signal === 'SELL').length;
    const totalTrades = llmTrades.length;

    return (
        <section className="flex flex-col gap-4 h-full animate-slide-up">
            <SectionHeading gradient="electric">How is the AI Feeling?</SectionHeading>

            <Card isHoverable padding="md" className="h-full flex flex-col justify-between gap-4">
                <div className="flex flex-col gap-4">
                    <SentimentHeader
                        emoji={sentiment.emoji}
                        label={sentiment.label}
                        direction={sentiment.direction}
                        isStale={isSentimentStale}
                        hasFeeling={!!marketFeeling}
                    />

                    {sentiment.confidence !== null && (
                        <div className="space-y-1">
                            <ConfidenceBar
                                label="Confidence"
                                value={sentiment.confidence}
                                colorScheme={getConfidenceColorScheme(sentiment.confidence)}
                                textStyle="default"
                                className="w-full"
                            />
                            <p className="text-xs font-normal text-boxel-muted">
                                Self-assessed conviction score generated by the AI meta-analyst.
                            </p>
                        </div>
                    )}

                    {sentiment.why && (
                        <p className="text-xs font-normal text-boxel-ink leading-relaxed italic border-l-2 border-accent pl-3">
                            "{sentiment.why}"
                        </p>
                    )}

                    {sentiment.primaryConcern && (
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Primary Concern:
                            </span>
                            <Badge colorScheme="neutral" size="xs">
                                {sentiment.primaryConcern}
                            </Badge>
                        </div>
                    )}

                    {totalTrades > 0 && <TradeSplit buyCount={buyCount} sellCount={sellCount} />}
                </div>

                <CardFooter
                    formattedTime={marketFeeling?.formattedTime}
                    modelUsed={marketFeeling?.model_used}
                />
            </Card>
        </section>
    );
}
