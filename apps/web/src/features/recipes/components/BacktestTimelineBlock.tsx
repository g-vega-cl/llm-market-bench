import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useEffect, useState } from 'react';
import type { BacktestDayStep, BacktestResultData, RecipeJobStatus } from '../types';

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
    return {
        label: `${first.action} ${first.ticker}${extra}`,
        colorScheme: first.action === 'BUY' ? 'success' : 'danger',
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
                    D{index + 1} • {day}
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
    const statusText = selectedStep
        ? `${selectedStep.trades_executed} executed • ${selectedStep.trades_skipped} skipped`
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
                    Day Trace: {activeDay}
                </span>
                <span className="text-xs font-normal text-boxel-muted">{statusText}</span>
            </div>

            {selectedStep ? (
                <div className="flex flex-col gap-2 min-w-0">
                    {selectedStep.tool_calls.length > 0 && (
                        <div className="flex flex-col gap-2 min-w-0">
                            <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                                Tools Called
                            </span>
                            <div className="flex flex-col gap-2">
                                {(() => {
                                    const seen = new Map<string, number>();
                                    return selectedStep.tool_calls.map((tc) => {
                                        const count = (seen.get(tc) ?? 0) + 1;
                                        seen.set(tc, count);
                                        return (
                                            <code
                                                key={`${tc}#${count}`}
                                                className="text-xs font-normal font-mono text-info break-all"
                                            >
                                                {tc}
                                            </code>
                                        );
                                    });
                                })()}
                            </div>
                        </div>
                    )}
                    <div className="flex flex-col gap-2 min-w-0">
                        <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                            Model Decision Output
                        </span>
                        <pre className="text-xs font-normal font-mono text-boxel-ink whitespace-pre-wrap break-words">
                            {selectedStep.output_excerpt || '(Empty model output)'}
                        </pre>
                    </div>
                </div>
            ) : (
                <p className="text-xs font-normal text-boxel-muted">
                    Select any settled day tile above to inspect its tool calls and decision trace.
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
                    {daySteps.length} / {windowDates.length || 10} Days Settled
                </span>
            </div>

            {windowDates.length === 0 ? (
                <div className="voxel-trough bg-boxel-trough p-4 flex flex-col gap-2">
                    <span className="text-sm font-bold text-boxel-ink">
                        Waiting for recipe worker to pick a 2-week historical window...
                    </span>
                    <span className="text-xs font-normal text-boxel-muted">
                        The worker daemon polls the queue every 5 seconds and streams each trading
                        day here as it finishes.
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
