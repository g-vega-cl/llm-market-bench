import type {
    Decision,
    MarketDataCache,
    MarketFeeling,
    Memory,
    NewsletterSnapshot,
    Trade,
} from '@llm-market-bench/database';
import { Badge, ConfidenceBar } from '@llm-market-bench/ui-design-system';

interface TodayStatusBarProps {
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

type ColorScheme = 'accent' | 'success' | 'danger' | 'info' | 'warning';

function getDirectionColor(direction: string | null | undefined): string {
    if (direction?.toUpperCase() === 'BULLISH') return 'text-neon-green-400';
    if (direction?.toUpperCase() === 'BEARISH') return 'text-alert-red-400';
    return 'text-steel-400';
}

function getDirectionColorScheme(direction: string | null | undefined): ColorScheme {
    if (direction === 'BULLISH') return 'success';
    if (direction === 'BEARISH') return 'danger';
    return 'neutral' as ColorScheme;
}

function getConfidenceColorScheme(score: number | null | undefined): ColorScheme {
    if (!score) return 'accent';
    if (score >= 70) return 'success';
    if (score >= 40) return 'warning';
    return 'danger';
}

// ── Sub-components to keep main function under complexity limit ──────────────

function MarketStatusChip({ isMarketOpen }: { isMarketOpen: boolean }) {
    return (
        <div className="flex items-center gap-1.5 shrink-0">
            <span
                className={
                    isMarketOpen ? 'live-dot' : 'w-2 h-2 rounded-full bg-zinc-400 dark:bg-zinc-600'
                }
            />
            <Badge
                variant="soft"
                colorScheme={isMarketOpen ? 'success' : 'neutral'}
                size="xs"
                radius="full"
            >
                {isMarketOpen ? 'MARKET OPEN' : 'MARKET CLOSED'}
            </Badge>
        </div>
    );
}

function SentimentSection({
    label,
    emoji,
    direction,
    confidence,
    isStale,
    hasFeeling,
}: {
    label: string;
    emoji: string;
    direction: string | null;
    confidence: number | null;
    isStale: boolean;
    hasFeeling: boolean;
}) {
    return (
        <>
            <div className="flex items-center gap-2 shrink-0">
                <span className="text-base">{emoji}</span>
                <span
                    className={`text-xs font-black uppercase tracking-wider ${getDirectionColor(direction)}`}
                >
                    {label}
                </span>
                {direction && (
                    <Badge
                        variant="soft"
                        size="xs"
                        colorScheme={getDirectionColorScheme(direction)}
                    >
                        {direction}
                    </Badge>
                )}
                {isStale && hasFeeling && (
                    <span
                        className="text-[9px] px-1.5 py-0.5 bg-amber-500/20 text-amber-400 rounded-full"
                        title="Data is older than 4 hours"
                    >
                        ⚠ STALE
                    </span>
                )}
            </div>

            {confidence !== null && (
                <>
                    <Divider />
                    <div className="flex items-center gap-2 shrink-0 min-w-[120px]">
                        <ConfidenceBar
                            label="Conf"
                            value={confidence}
                            colorScheme={getConfidenceColorScheme(confidence)}
                            textStyle="default"
                            className="w-full"
                        />
                    </div>
                </>
            )}
        </>
    );
}

function AnalysisTimestamp({
    formattedTime,
    modelUsed,
}: {
    formattedTime?: string;
    modelUsed?: string | null;
}) {
    return (
        <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] text-zinc-500 dark:text-zinc-500 font-mono tabular-nums">
                {formattedTime ? `Last analyzed: ${formattedTime}` : 'Waiting for analysis...'}
            </span>
            {modelUsed && (
                <span className="text-[10px] text-zinc-600 dark:text-zinc-600 font-mono">
                    • {modelUsed}
                </span>
            )}
        </div>
    );
}

// ── Main bar ─────────────────────────────────────────────────────────────────

export function TodayStatusBar({ data }: TodayStatusBarProps) {
    const { isMarketOpen, isSentimentStale, todayDateString, marketFeeling } = data;

    const totalTrades = data.trades?.length ?? 0;
    const activeMemories = data.memories?.filter((m) => m.status === 'ACTIVE').length ?? 0;
    const buyCount = data.trades?.filter((t) => t.signal === 'BUY').length ?? 0;
    const sellCount = data.trades?.filter((t) => t.signal === 'SELL').length ?? 0;
    const newsletterCount = data.newsletters?.length ?? 0;

    const sentiment = {
        label: marketFeeling?.sentiment_label ?? 'Analyzing...',
        emoji: marketFeeling?.sentiment_emoji ?? '🤔',
        direction: marketFeeling?.market_direction ?? null,
        confidence: marketFeeling?.confidence_score ?? null,
    };

    return (
        <div className="sticky top-[57px] z-40 border-b border-zinc-200 dark:border-zinc-800 bg-white/85 dark:bg-zinc-950/85 backdrop-blur-md px-4 md:px-8 py-2">
            <div className="flex items-center gap-4 overflow-x-auto scrollbar-hide whitespace-nowrap min-h-[40px]">
                {/* Label + date */}
                <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs font-black uppercase tracking-widest text-zinc-900 dark:text-zinc-100 font-mono">
                        TODAY
                    </span>
                    <span className="text-zinc-300 dark:text-zinc-700">•</span>
                    <span className="text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest tabular-nums">
                        {todayDateString}
                    </span>
                </div>

                <Divider />
                <MarketStatusChip isMarketOpen={isMarketOpen} />
                <Divider />

                <SentimentSection
                    label={sentiment.label}
                    emoji={sentiment.emoji}
                    direction={sentiment.direction}
                    confidence={sentiment.confidence}
                    isStale={isSentimentStale}
                    hasFeeling={!!marketFeeling}
                />

                <Divider />

                {/* Trade counts */}
                <div className="flex items-center gap-3 shrink-0">
                    <StatChip color="text-neon-green-400" label="BUY" value={buyCount} />
                    <StatChip color="text-alert-red-400" label="SELL" value={sellCount} />
                    <StatChip color="text-electric-blue-400" label="TRADES" value={totalTrades} />
                </div>

                <Divider />

                {/* Briefs & memories */}
                <div className="flex items-center gap-3 shrink-0">
                    <StatChip color="text-zinc-400" label="BRIEFS" value={newsletterCount} />
                    <StatChip color="text-zinc-400" label="MEMORIES" value={activeMemories} />
                </div>

                <Divider />

                <AnalysisTimestamp
                    formattedTime={marketFeeling?.formattedTime}
                    modelUsed={marketFeeling?.model_used}
                />
            </div>
        </div>
    );
}

function Divider() {
    return <span className="text-zinc-300 dark:text-zinc-700 shrink-0">|</span>;
}

function StatChip({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div className="flex items-center gap-1">
            <span className={`text-xs font-black tabular-nums ${color}`}>{value}</span>
            <span className="text-[9px] font-bold text-zinc-500 dark:text-zinc-500 uppercase tracking-widest">
                {label}
            </span>
        </div>
    );
}
