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
        <section className="flex flex-col gap-6 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading>Horizon Watch: Pending Events</SectionHeading>

                <div className="flex items-center gap-2 px-4 py-2 bg-voxel-trough border border-voxel-bevel-hi rounded-none shadow-sm">
                    <span className="text-sm font-bold text-accent uppercase tracking-wider">
                        📅 {visibleEvents.length} Catalyst{visibleEvents.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            {/* Timeline View */}
            <div className="relative">
                {/* Timeline Line */}
                <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyber-yellow-500 via-amber-500 to-transparent opacity-30" />

                <div className="flex flex-col gap-4">
                    {visibleEvents.map((event, idx) => {
                        const dateNote = event.metadata?.future_date_note;
                        const importanceScore =
                            event.importance_score ?? event.metadata?.importance_score ?? 7;

                        return (
                            <div
                                key={event.id}
                                className="relative pl-20 animate-slide-up group"
                                style={{ animationDelay: `${idx * 100}ms` }}
                            >
                                {/* Timeline Dot */}
                                <div
                                    className={`absolute left-6 top-6 w-4 h-4 rounded-none border-2 border-voxel-canvas shadow-sm bg-gradient-to-br ${getImportanceColor(importanceScore)} z-10 transition-all duration-300`}
                                />

                                {/* Card */}
                                <Card
                                    isHoverable
                                    className="border-l-2 hover:shadow-cyber-yellow-500/10 rounded-none shadow-sm flex flex-col gap-4"
                                    style={{
                                        borderLeftColor:
                                            importanceScore >= 8 ? '#ef4444' : '#eab308',
                                    }}
                                >
                                    {/* Header */}
                                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                                        <div className="flex-1 min-w-0 flex flex-col gap-2">
                                            {/* Date & Time Badge */}
                                            <div className="flex flex-wrap items-center gap-2">
                                                {dateNote && (
                                                    <Badge
                                                        variant="soft"
                                                        colorScheme="neutral"
                                                        size="xs"
                                                    >
                                                        {dateNote}
                                                    </Badge>
                                                )}
                                                <Badge
                                                    colorScheme={
                                                        importanceScore >= 8 ? 'warning' : 'info'
                                                    }
                                                    variant="soft"
                                                    size="sm"
                                                >
                                                    {getImportanceLabel(importanceScore)}
                                                </Badge>
                                            </div>

                                            {/* Event Time if available */}
                                            {event.metadata?.event_time &&
                                                event.metadata.event_time !== 'N/A' && (
                                                    <div className="flex items-center gap-1.5 text-xs font-normal text-voxel-muted">
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
                                                <div className="text-sm font-bold font-mono text-voxel-ink">
                                                    {normalizeWhitespace(
                                                        event.formattedTargetMonthDay,
                                                    )}
                                                </div>
                                                <div className="text-xs font-normal text-voxel-muted font-mono uppercase tracking-wider">
                                                    {normalizeWhitespace(
                                                        event.formattedTargetYear || '',
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Content */}
                                    <p className="text-sm font-bold text-voxel-ink leading-relaxed">
                                        {event.content}
                                    </p>

                                    {/* Scenario Analysis */}
                                    {event.metadata?.scenario_analysis && (
                                        <div className="pt-4 border-t border-voxel-bevel-lo flex flex-col gap-3">
                                            <div className="flex items-center gap-2">
                                                <span className="text-lg">🔮</span>
                                                <h4 className="text-sm font-bold text-accent uppercase tracking-wider">
                                                    Scenarios & Trading Plans
                                                </h4>
                                            </div>
                                            <div className="bg-voxel-trough p-4 rounded-none border border-voxel-bevel-hi">
                                                <div className="flex flex-col gap-1">
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
                                                                    className="tabular-nums mt-0.5"
                                                                >
                                                                    {line.percentage}
                                                                </Badge>
                                                            )}
                                                            <span className="text-xs font-normal text-voxel-ink leading-relaxed">
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
                                            <div className="pt-2 flex flex-wrap gap-2">
                                                {event.metadata.tickers.map(
                                                    (ticker: string, i: number) => (
                                                        <span
                                                            key={i}
                                                            className="px-3 py-1.5 bg-voxel-trough text-voxel-ink text-sm font-bold rounded-none uppercase tracking-wider border border-voxel-bevel-hi hover:border-accent hover:text-accent transition-all duration-300 cursor-default"
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
