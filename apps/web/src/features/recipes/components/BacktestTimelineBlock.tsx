import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import type { BacktestDayStep, BacktestResultData, RecipeJobStatus } from '../types';

export interface BacktestTimelineSelection {
    windowDates: string[];
    daySteps: BacktestDayStep[];
    stepByDay: Map<string, BacktestDayStep>;
    activeDay: string | null;
    activeIndex: number;
    selectedStep: BacktestDayStep | undefined;
    isRunning: boolean;
    currentRunningDay: string | null;
    isCurrentRunning: boolean;
}

interface BacktestTimelineBlockProps {
    queuePosition?: number | null;
    selection: BacktestTimelineSelection;
    onSelectDay: (day: string) => void;
}

export function resolveBacktestTimelineSelection(
    status: RecipeJobStatus,
    results: BacktestResultData | null,
    manualSelectedDay: string | null,
): BacktestTimelineSelection {
    const windowDates = results?.window_dates ?? [];
    const daySteps = results?.day_steps ?? [];
    const stepByDay = new Map(daySteps.map((s) => [s.day, s]));
    const latestCompletedDay = daySteps.length > 0 ? daySteps[daySteps.length - 1]?.day : null;
    const validLatestCompleted =
        latestCompletedDay && windowDates.includes(latestCompletedDay) ? latestCompletedDay : null;
    const activeDay =
        manualSelectedDay && windowDates.includes(manualSelectedDay)
            ? manualSelectedDay
            : (validLatestCompleted ?? windowDates[0] ?? null);
    const activeIndex = activeDay ? windowDates.indexOf(activeDay) : -1;
    const selectedStep = activeDay ? stepByDay.get(activeDay) : undefined;
    const isRunning = status === 'pending' || status === 'processing';
    const currentRunningDay = isRunning ? (results?.current_day ?? null) : null;

    return {
        windowDates,
        daySteps,
        stepByDay,
        activeDay,
        activeIndex,
        selectedStep,
        isRunning,
        currentRunningDay,
        isCurrentRunning: Boolean(activeDay && currentRunningDay === activeDay),
    };
}

export function formatDayStatusText(
    selectedStep: BacktestDayStep | undefined,
    isCurrentRunning: boolean,
): string {
    if (!selectedStep) {
        return isCurrentRunning
            ? 'Running LLM evaluation for this session...'
            : 'Waiting in timeline queue';
    }
    const openCount =
        typeof selectedStep.open_positions_count === 'number'
            ? ` • ${selectedStep.open_positions_count} open`
            : '';
    return `${selectedStep.trades_executed} executed • ${selectedStep.trades_skipped} skipped${openCount}`;
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

function SelectedSlotBar({
    activeDay,
    activeIndex,
    selectedStep,
    isCurrentRunning,
}: {
    activeDay: string;
    activeIndex: number;
    selectedStep: BacktestDayStep | undefined;
    isCurrentRunning: boolean;
}) {
    const badge = formatDaySignal(selectedStep, isCurrentRunning);
    const statusText = formatDayStatusText(selectedStep, isCurrentRunning);

    return (
        <div
            data-testid="selected-slot-bar"
            className="voxel-trough bg-boxel-trough px-4 py-3 flex flex-wrap items-center justify-between gap-3 min-w-0"
        >
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 min-w-0">
                <span className="text-sm font-bold font-mono text-boxel-ink whitespace-nowrap">
                    S{activeIndex + 1} • {activeDay}
                </span>
                <Badge
                    size="xs"
                    variant={selectedStep || isCurrentRunning ? 'soft' : 'outline'}
                    colorScheme={badge.colorScheme}
                >
                    {badge.label}
                </Badge>
                <span className="text-xs font-normal text-boxel-muted whitespace-nowrap">
                    {statusText}
                </span>
            </div>
            <a
                href="#session-trace"
                className="voxel-btn inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-bold border border-accent text-accent bg-boxel-surface hover:bg-boxel-elevated rounded-none whitespace-nowrap"
            >
                Jump to Trace ↓
            </a>
        </div>
    );
}

export function BacktestTimelineBlock({
    queuePosition = null,
    selection,
    onSelectDay,
}: BacktestTimelineBlockProps) {
    const {
        windowDates,
        daySteps,
        stepByDay,
        activeDay,
        activeIndex,
        selectedStep,
        isRunning,
        currentRunningDay,
        isCurrentRunning,
    } = selection;

    return (
        <section id="simulation-timeline" className="min-w-0 scroll-mt-4">
            <Card padding="md" className="flex flex-col gap-4 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-boxel-bevel-hi pb-3">
                    <SectionHeading gradient="electric">Simulation Timeline</SectionHeading>
                    <span className="text-xs font-normal font-mono tabular-nums text-boxel-muted whitespace-nowrap">
                        {daySteps.length} / {windowDates.length || 30} Sessions Settled
                    </span>
                </div>

                {windowDates.length === 0 ? (
                    <div className="voxel-trough bg-boxel-trough p-4 flex flex-col gap-2">
                        <span className="text-sm font-bold text-boxel-ink">
                            {queuePosition && queuePosition > 0
                                ? `Queued (#${queuePosition} in line) — Waiting for recipe worker to pick a 2-week historical window...`
                                : 'Waiting for recipe worker to pick a 2-week historical window...'}
                        </span>
                        <span className="text-xs font-normal text-boxel-muted">
                            Single-GPU Strata runs 1 backtest globally at a time (strata-auto-go)
                            while streaming each 3x/day ET session here. You can safely close this
                            tab or cancel anytime.
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
                                        isRunning &&
                                            !stepByDay.get(day) &&
                                            currentRunningDay === day,
                                    )}
                                    isSelected={activeDay === day}
                                    onSelect={onSelectDay}
                                />
                            ))}
                        </div>

                        {activeDay && (
                            <SelectedSlotBar
                                activeDay={activeDay}
                                activeIndex={activeIndex}
                                selectedStep={selectedStep}
                                isCurrentRunning={isCurrentRunning}
                            />
                        )}
                    </>
                )}
            </Card>
        </section>
    );
}
