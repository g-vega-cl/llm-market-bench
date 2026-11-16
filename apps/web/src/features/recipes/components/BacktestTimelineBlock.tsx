import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useEffect, useState } from 'react';
import type { BacktestDayStep, BacktestResultData, RecipeJobStatus } from '../types';
import { TraceInspectorBlock } from './TraceInspectorBlock';

interface BacktestTimelineBlockProps {
    status: RecipeJobStatus;
    results: BacktestResultData | null;
}

function formatDaySignal(
    step: BacktestDayStep | undefined,
    isCurrent: boolean,
): {
    label: string;
    colorScheme: 'success' | 'danger' | 'accent' | 'neutral' | 'warning';
} {
    if (!step) {
        return isCurrent
            ? { label: 'RUNNING', colorScheme: 'accent' }
            : { label: 'QUEUED', colorScheme: 'neutral' };
    }
    if (step.status === 'error') {
        return { label: 'ERROR', colorScheme: 'danger' };
    }
    if (step.signals.length === 0) {
        return { label: 'HOLD', colorScheme: 'neutral' };
    }
    const first = step.signals[0];
    const extra = step.signals.length > 1 ? ` +${step.signals.length - 1}` : '';
    const colorScheme =
        first.action === 'BUY' ? 'success' : first.action === 'EXIT' ? 'warning' : 'danger';
    return {
        label: `${first.action} ${first.ticker}${extra}`,
        colorScheme,
    };
}

function formatSignedCurrency(amount: number): string {
    const abs = Math.abs(amount).toFixed(2);
    return `${amount >= 0 ? '+' : '-'}$${abs}`;
}

function DayTile({
    day,
    index,
    step,
    isCurrent,
    isSelected,
    onSelect,
}: {
    day: string;
    index: number;
    step: BacktestDayStep | undefined;
    isCurrent: boolean;
    isSelected: boolean;
    onSelect: (day: string) => void;
}) {
    const badge = formatDaySignal(step, isCurrent);
    const tileStyle = isSelected
        ? 'bg-boxel-elevated border-2 border-accent'
        : isCurrent
          ? 'bg-boxel-surface border border-accent'
          : 'bg-boxel-trough hover:bg-boxel-elevated';
    const pnlColor = !step
        ? 'text-boxel-muted'
        : step.day_pnl_net >= 0
          ? 'text-success'
          : 'text-danger';

    return (
        <button
            type="button"
            aria-pressed={isSelected}
            onClick={() => onSelect(day)}
            className={`voxel-trough rounded-none p-3 text-left flex flex-col gap-2 min-w-0 transition-colors ${tileStyle}`}
        >
            <div className="flex flex-wrap items-baseline justify-between gap-2 min-w-0">
                <span className="text-xs font-normal font-mono tabular-nums text-boxel-ink whitespace-nowrap">
                    S{index + 1} • {day}
                </span>
                <span
                    className={`text-xs font-normal font-mono tabular-nums whitespace-nowrap ${pnlColor}`}
                >
                    {step ? formatSignedCurrency(step.day_pnl_net) : '--'}
                </span>
            </div>
            <div className="flex items-center justify-between gap-2 min-w-0">
                <Badge
                    size="xs"
                    variant={step || isCurrent ? 'soft' : 'outline'}
                    colorScheme={badge.colorScheme}
                >
                    {badge.label}
                </Badge>
            </div>
        </button>
    );
}

function DayInspector({
    activeDay,
    selectedStep,
    isCurrentRunning,
}: {
    activeDay: string | null;
    selectedStep: BacktestDayStep | undefined;
    isCurrentRunning: boolean;
}) {
    const openCount =
        selectedStep && typeof selectedStep.open_positions_count === 'number'
            ? ` • ${selectedStep.open_positions_count} open`
            : '';
    const statusText = selectedStep
        ? `${selectedStep.trades_executed} executed • ${selectedStep.trades_skipped} skipped${openCount}`
        : isCurrentRunning
          ? 'Running LLM evaluation for this session...'
          : 'Waiting in timeline queue';

    return (
        <div
            data-testid="day-inspector-trough"
            className="voxel-trough bg-boxel-trough p-4 flex flex-col gap-4 min-w-0"
        >
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-boxel-bevel-lo pb-2">
                <span className="text-sm font-bold text-boxel-ink whitespace-nowrap">
                    Session Trace: {activeDay}
                </span>
                <span className="text-xs font-normal text-boxel-muted">{statusText}</span>
            </div>

            {selectedStep ? (
                <TraceInspectorBlock
                    prompt={selectedStep.prompt}
                    trace={selectedStep.trace}
                    toolCalls={selectedStep.tool_calls}
                    fullOutput={selectedStep.full_output}
                    outputExcerpt={selectedStep.output_excerpt}
                />
            ) : (
                <p className="text-xs font-normal text-boxel-muted">
                    Select any settled session tile above to inspect its tool calls and decision
                    trace.
                </p>
            )}
        </div>
    );
}

export function BacktestTimelineBlock({ status, results }: BacktestTimelineBlockProps) {
    const windowDates = results?.window_dates ?? [];
    const daySteps = results?.day_steps ?? [];
    const stepByDay = new Map(daySteps.map((s) => [s.day, s]));
    const latestCompletedDay = daySteps.length > 0 ? daySteps[daySteps.length - 1]?.day : null;

    const [manualSelectedDay, setManualSelectedDay] = useState<string | null>(null);
    const activeDay =
        manualSelectedDay && windowDates.includes(manualSelectedDay)
            ? manualSelectedDay
            : (latestCompletedDay ?? windowDates[0] ?? null);

    useEffect(() => {
        if (manualSelectedDay && !windowDates.includes(manualSelectedDay)) {
            setManualSelectedDay(null);
        }
    }, [manualSelectedDay, windowDates]);

    const selectedStep = activeDay ? stepByDay.get(activeDay) : undefined;
    const isRunning = status === 'pending' || status === 'processing';
    const currentRunningDay = isRunning ? (results?.current_day ?? null) : null;

    return (
        <Card padding="md" className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-boxel-bevel-hi pb-3">
                <SectionHeading gradient="electric">Simulation Timeline</SectionHeading>
                <span className="text-xs font-normal font-mono tabular-nums text-boxel-muted">
                    {daySteps.length} / {windowDates.length || 30} Sessions Settled
                </span>
            </div>

            {windowDates.length === 0 ? (
                <div className="voxel-trough bg-boxel-trough p-4 flex flex-col gap-2">
                    <span className="text-sm font-bold text-boxel-ink">
                        Waiting for recipe worker to pick a 2-week historical window...
                    </span>
                    <span className="text-xs font-normal text-boxel-muted">
                        The worker daemon polls the queue every 5 seconds and streams each 3x/day ET
                        session here as it finishes.
                    </span>
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,10.5rem),1fr))] gap-2">
                        {windowDates.map((day, idx) => (
                            <DayTile
                                key={day}
                                day={day}
                                index={idx}
                                step={stepByDay.get(day)}
                                isCurrent={Boolean(
                                    isRunning && !stepByDay.get(day) && currentRunningDay === day,
                                )}
                                isSelected={activeDay === day}
                                onSelect={setManualSelectedDay}
                            />
                        ))}
                    </div>

                    <DayInspector
                        activeDay={activeDay}
                        selectedStep={selectedStep}
                        isCurrentRunning={currentRunningDay === activeDay}
                    />
                </>
            )}
        </Card>
    );
}
