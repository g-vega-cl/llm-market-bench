import { Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import type { BacktestDayStep } from '../types';
import { formatDayStatusText } from './BacktestTimelineBlock';
import { TraceInspectorBlock } from './TraceInspectorBlock';

interface BacktestSessionTraceBlockProps {
    windowDates: string[];
    activeDay: string | null;
    activeIndex: number;
    selectedStep: BacktestDayStep | undefined;
    isCurrentRunning: boolean;
    onSelectDay: (day: string) => void;
}

function HoldSummaryNotice({ selectedStep }: { selectedStep: BacktestDayStep }) {
    if (selectedStep.signals.length > 0) return null;
    const toolCount = selectedStep.tool_calls?.length ?? 0;
    const roundCount = selectedStep.trace?.rounds?.length ?? (toolCount > 0 ? 1 : 0);
    return (
        <div className="border border-voxel-bevel-lo bg-voxel-surface px-3 py-2 text-xs font-normal text-voxel-muted">
            Hold decision: evaluated {toolCount} PIT tool {toolCount === 1 ? 'call' : 'calls'}{' '}
            across {roundCount} reasoning {roundCount === 1 ? 'round' : 'rounds'} and stayed in cash
            / existing positions ([]).
        </div>
    );
}

export function BacktestSessionTraceBlock({
    windowDates,
    activeDay,
    activeIndex,
    selectedStep,
    isCurrentRunning,
    onSelectDay,
}: BacktestSessionTraceBlockProps) {
    if (windowDates.length === 0 || !activeDay) {
        return null;
    }

    const statusText = formatDayStatusText(selectedStep, isCurrentRunning);
    const prevDay = activeIndex > 0 ? windowDates[activeIndex - 1] : null;
    const nextDay =
        activeIndex >= 0 && activeIndex < windowDates.length - 1
            ? windowDates[activeIndex + 1]
            : null;

    return (
        <section id="session-trace" className="min-w-0 scroll-mt-4">
            <Card padding="md" className="flex flex-col gap-4 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-voxel-bevel-hi pb-3 min-w-0">
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 min-w-0">
                        <SectionHeading>Session Trace</SectionHeading>
                        <span className="text-xs font-normal font-mono tabular-nums text-voxel-muted whitespace-nowrap">
                            S{activeIndex + 1} / {windowDates.length} • {activeDay}
                        </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        <Button
                            size="sm"
                            variant="outline"
                            disabled={!prevDay}
                            onClick={() => prevDay && onSelectDay(prevDay)}
                        >
                            ‹ Prev
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            disabled={!nextDay}
                            onClick={() => nextDay && onSelectDay(nextDay)}
                        >
                            Next ›
                        </Button>
                        <a
                            href="#simulation-timeline"
                            className="voxel-btn inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-bold border border-voxel-bevel-hi text-voxel-ink bg-voxel-surface hover:bg-voxel-elevated rounded-none whitespace-nowrap"
                        >
                            ↑ Timeline
                        </a>
                    </div>
                </div>

                <div
                    data-testid="day-inspector-trough"
                    className="voxel-trough bg-voxel-trough p-4 flex flex-col gap-4 min-w-0"
                >
                    <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-voxel-bevel-lo pb-2 min-w-0">
                        <span className="text-sm font-bold text-voxel-ink whitespace-nowrap">
                            Session Trace: {activeDay}
                        </span>
                        <span className="text-xs font-normal text-voxel-muted">{statusText}</span>
                    </div>

                    {selectedStep ? (
                        <div className="flex flex-col gap-3 min-w-0">
                            <HoldSummaryNotice selectedStep={selectedStep} />
                            <TraceInspectorBlock
                                prompt={selectedStep.prompt}
                                trace={selectedStep.trace}
                                toolCalls={selectedStep.tool_calls}
                                fullOutput={selectedStep.full_output}
                                outputExcerpt={selectedStep.output_excerpt}
                            />
                        </div>
                    ) : (
                        <p className="text-xs font-normal text-voxel-muted">
                            Select any settled session tile in the timeline above to inspect its
                            tool calls and decision trace.
                        </p>
                    )}
                </div>
            </Card>
        </section>
    );
}
