import type { Memory } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { parseScenarioPercentages } from '~/lib/parse-scenario-percentages';
import { normalizeWhitespace } from '~/utils/date';

interface FutureEventItem extends Memory {
    formattedTargetMonthDay?: string;
    formattedTargetYear?: string;
}

interface FutureCatalystsProps {
    events: FutureEventItem[];
}

function extractDate(content: string): string | null {
    const match = content.match(/(\d{4}-\d{2}-\d{2})/);
    return match ? match[1] : null;
}

function getImportanceColor(score: number) {
    if (score >= 9) return 'from-alert-red-500 to-rose-600';
    if (score >= 8) return 'from-cyber-yellow-500 to-amber-600';
    if (score >= 6) return 'from-electric-blue-500 to-blue-600';
    return 'from-steel-400 to-zinc-500';
}

function getImportanceLabel(score: number) {
    if (score >= 9) return 'Critical';
    if (score >= 8) return 'High';
    if (score >= 6) return 'Medium';
    return 'Low';
}

export function FutureCatalysts({ events }: FutureCatalystsProps) {
    if (!events.length) return null;

    // Sort by date
    const visibleEvents = [...events].sort((a, b) => {
        const dateA = a.target_date || extractDate(a.content);
        const dateB = b.target_date || extractDate(b.content);
        if (!dateA && !dateB) return 0;
        if (!dateA) return 1;
        if (!dateB) return -1;
        return new Date(dateA).getTime() - new Date(dateB).getTime();
    });

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading gradient="catalyst">Horizon Watch: Pending Events</SectionHeading>

                <div className="flex items-center gap-2 px-4 py-2 bg-cyber-yellow-50 dark:bg-cyber-yellow-950/20 border border-cyber-yellow-200 dark:border-cyber-yellow-900/30 rounded-xl shadow-md">
                    <span className="text-[10px] font-black text-cyber-yellow-600 dark:text-cyber-yellow-400 uppercase tracking-widest">
                        📅 {visibleEvents.length} Catalyst{visibleEvents.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            {/* Timeline View */}
            <div className="relative">
                {/* Timeline Line */}
                <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyber-yellow-500 via-amber-500 to-transparent opacity-30" />

                <div className="space-y-4">
                    {visibleEvents.map((event, idx) => {
                        const dateNote = event.metadata?.future_date_note;
                        const importanceScore = event.metadata?.importance_score || 7;

                        return (
                            <div
                                key={event.id}
                                className="relative pl-20 animate-slide-up group"
                                style={{ animationDelay: `${idx * 100}ms` }}
                            >
                                {/* Timeline Dot */}
                                <div
                                    className={`absolute left-6 top-6 w-5 h-5 rounded-full border-4 border-white dark:border-zinc-950 shadow-lg bg-gradient-to-br ${getImportanceColor(importanceScore)} z-10 group-hover:scale-125 group-hover:shadow-xl transition-all duration-300`}
                                />

                                {/* Card */}
                                <Card
                                    isHoverable
                                    className="border-l-4 hover:shadow-cyber-yellow-500/10"
                                    style={{
                                        borderLeftColor:
                                            importanceScore >= 8 ? '#ef4444' : '#eab308',
                                    }}
                                >
                                    {/* Header */}
                                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-4">
                                        <div className="flex-1 min-w-0">
                                            {/* Date & Time Badge */}
                                            <div className="flex flex-wrap items-center gap-2 mb-3">
                                                {dateNote && (
                                                    <Badge
                                                        variant="soft"
                                                        colorScheme="neutral"
                                                        size="xs"
                                                        radius="md"
                                                    >
                                                        {dateNote}
                                                    </Badge>
                                                )}
                                                <Badge
                                                    severity={
                                                        importanceScore >= 8 ? 'high' : 'medium'
                                                    }
                                                    variant="soft"
                                                    radius="lg"
                                                    size="sm"
                                                >
                                                    {getImportanceLabel(importanceScore)}
                                                </Badge>
                                            </div>

                                            {/* Event Time if available */}
                                            {event.metadata?.event_time &&
                                                event.metadata.event_time !== 'N/A' && (
                                                    <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400 mb-2">
                                                        <span>🕐</span>
                                                        <span className="font-mono tabular-nums">
                                                            {event.metadata.event_time}
                                                        </span>
                                                    </div>
                                                )}
                                        </div>

                                        {/* Date Display */}
                                        {event.formattedTargetMonthDay && (
                                            <div className="text-right">
                                                <div className="text-2xl font-black text-zinc-900 dark:text-white text-display">
                                                    {normalizeWhitespace(
                                                        event.formattedTargetMonthDay,
                                                    )}
                                                </div>
                                                <div className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider">
                                                    {normalizeWhitespace(
                                                        event.formattedTargetYear || '',
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Content */}
                                    <p className="text-base text-zinc-800 dark:text-zinc-200 font-bold leading-relaxed mb-4">
                                        {event.content}
                                    </p>

                                    {/* Scenario Analysis */}
                                    {event.metadata?.scenario_analysis && (
                                        <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800">
                                            <div className="flex items-center gap-2 mb-3">
                                                <span className="text-lg">🔮</span>
                                                <h4 className="text-[10px] font-black text-cyber-yellow-600 dark:text-cyber-yellow-400 uppercase tracking-widest">
                                                    Scenarios & Trading Plans
                                                </h4>
                                            </div>
                                            <div className="bg-gradient-to-br from-cyber-yellow-50/50 via-amber-50/30 to-transparent dark:from-cyber-yellow-950/10 dark:via-amber-950/5 p-4 rounded-2xl border border-cyber-yellow-100 dark:border-cyber-yellow-900/30">
                                                <div className="space-y-1">
                                                    {parseScenarioPercentages(
                                                        event.metadata.scenario_analysis,
                                                    ).map((line, i) => (
                                                        <div
                                                            key={i}
                                                            className="flex items-start gap-2"
                                                        >
                                                            {line.percentage && (
                                                                <Badge
                                                                    size="xs"
                                                                    variant="soft"
                                                                    colorScheme="warning"
                                                                    radius="md"
                                                                    className="tabular-nums mt-0.5"
                                                                >
                                                                    {line.percentage}
                                                                </Badge>
                                                            )}
                                                            <span className="text-[11px] text-zinc-700 dark:text-zinc-300 font-medium leading-relaxed">
                                                                {line.text}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Tickers if available */}
                                    {event.metadata?.tickers &&
                                        event.metadata.tickers.length > 0 && (
                                            <div className="mt-4 flex flex-wrap gap-2">
                                                {event.metadata.tickers.map(
                                                    (ticker: string, i: number) => (
                                                        <span
                                                            key={i}
                                                            className="px-3 py-1.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-[10px] font-bold rounded-lg uppercase tracking-wider border border-zinc-200 dark:border-zinc-700 hover:border-cyber-yellow-500 hover:text-cyber-yellow-600 dark:hover:text-cyber-yellow-400 transition-all duration-300 cursor-default"
                                                        >
                                                            {ticker}
                                                        </span>
                                                    ),
                                                )}
                                            </div>
                                        )}
                                </Card>
                            </div>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}
