import {
    Badge,
    Button,
    Card,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { RecipePortfolioBlock } from '../components/RecipePortfolioBlock';
import { TraceInspectorBlock } from '../components/TraceInspectorBlock';
import type { LivePortfolioSnapshot, LiveRunResult, RecipeJobRecord } from '../types';

const INLINE_LATEST_ID = 'inline-latest';

interface RecipeLivePageProps {
    recipeId: string;
    initialData: {
        portfolio: LivePortfolioSnapshot;
        recentLiveRuns: RecipeJobRecord[];
    } | null;
}

function extractLiveResult(job: RecipeJobRecord | undefined): LiveRunResult | null {
    if (!job?.result_json) return null;
    if ('mode' in job.result_json && job.result_json.mode === 'live_turn') {
        return job.result_json as LiveRunResult;
    }
    return null;
}

function getNextSlotLabel(now: Date): string {
    // 09:30, 12:30, 15:30 ET, Mon-Fri.
    const etOffset = -4; // EDT
    const etNow = new Date(now.getTime() + etOffset * 60 * 60 * 1000);
    if (etNow.getDay() < 1 || etNow.getDay() > 5) return '09:30 ET Monday';

    const slotsET = [9.5, 12.5, 15.5];
    const currentHour = etNow.getHours() + etNow.getMinutes() / 60;
    const nextSlot = slotsET.find((s) => s > currentHour);
    if (nextSlot === undefined) return '09:30 ET tomorrow';

    const hour = Math.floor(nextSlot);
    const minute = Math.round((nextSlot - hour) * 60);
    return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')} ET today`;
}

interface RunSelectorBarProps {
    recentLiveRuns: RecipeJobRecord[];
    hasLatestInline: boolean;
    isViewingInline: boolean;
    activeJobId: string | undefined;
    onSelect: (id: string) => void;
}

function RunSelectorBar({
    recentLiveRuns,
    hasLatestInline,
    isViewingInline,
    activeJobId,
    onSelect,
}: RunSelectorBarProps) {
    if (!hasLatestInline && recentLiveRuns.length === 0) return null;
    return (
        <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-normal text-voxel-muted">Recent Live Turns:</span>
            {hasLatestInline && (
                <Button
                    size="sm"
                    variant={isViewingInline ? 'solid' : 'outline'}
                    onClick={() => onSelect(INLINE_LATEST_ID)}
                >
                    Latest Turn
                </Button>
            )}
            {recentLiveRuns.map((run) => {
                const isSelected = !isViewingInline && activeJobId === run.id;
                const stamp = (run.created_at || '').slice(0, 16).replace('T', ' ');
                return (
                    <Button
                        key={run.id}
                        size="sm"
                        variant={isSelected ? 'solid' : 'outline'}
                        onClick={() => onSelect(run.id)}
                    >
                        {stamp || run.id.slice(0, 8)}
                    </Button>
                );
            })}
        </div>
    );
}

export function RecipeLivePage({ recipeId, initialData }: RecipeLivePageProps) {
    const [selectedRunId, setSelectedRunId] = useState<string | null>(
        () => initialData?.recentLiveRuns[0]?.id ?? null,
    );

    const recentLiveRuns = initialData?.recentLiveRuns ?? [];
    const portfolio = initialData?.portfolio ?? null;

    const activeSelection = selectedRunId ?? recentLiveRuns[0]?.id ?? null;
    const activeJob = recentLiveRuns.find((run) => run.id === activeSelection) ?? recentLiveRuns[0];
    const _isViewingInline = false; // No inline latest on this page
    const activeRun = extractLiveResult(activeJob);

    const hasPortfolio = portfolio !== null;
    const hasRuns = recentLiveRuns.length > 0;

    const nextSlotLabel = getNextSlotLabel(new Date());

    return (
        <PageLayout>
            <div className="flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-4">
                    <div className="flex items-center gap-3">
                        <Link
                            to="/recipes"
                            className="voxel-btn inline-flex items-center gap-2 px-3 py-1.5 text-sm font-bold border border-voxel-bevel-hi bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated rounded-none"
                        >
                            ← Back to Studio
                        </Link>
                        <div>
                            <h1 className="type-heading text-voxel-ink">Live Status</h1>
                            <span className="type-body text-voxel-muted">
                                Recipe ID: {recipeId.slice(0, 8)}
                            </span>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="soft" colorScheme="success" size="sm">
                            Live: ON (3x/d)
                        </Badge>
                        <span className="type-body text-voxel-muted">
                            Next run: {nextSlotLabel}
                        </span>
                    </div>
                </div>

                {hasPortfolio && (
                    <RecipePortfolioBlock
                        title="Live Paper Portfolio"
                        cash={portfolio.cash}
                        totalEquity={portfolio.total_equity}
                        openPositions={portfolio.open_positions}
                    />
                )}

                {hasRuns && (
                    <Card padding="md" className="flex flex-col gap-4 min-w-0">
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-3">
                            <div className="flex flex-col gap-1 min-w-0">
                                <SectionHeading>Live Run Traces</SectionHeading>
                                <span className="text-xs font-normal text-voxel-muted">
                                    Runs independently on clvg.uk auto-go against your isolated
                                    $10,000 live paper ledger (scheduled 3x/day ET at 09:30, 12:30,
                                    15:30).
                                </span>
                            </div>
                            {activeRun && (
                                <div className="flex flex-wrap items-center gap-2">
                                    <Badge variant="soft" size="xs">
                                        {activeRun.slot_label || activeRun.as_of_utc.slice(0, 16)}
                                    </Badge>
                                    <Badge variant="soft" colorScheme="accent" size="xs">
                                        {activeRun.signals.length} Signals
                                    </Badge>
                                </div>
                            )}
                        </div>

                        <RunSelectorBar
                            recentLiveRuns={recentLiveRuns}
                            hasLatestInline={false}
                            isViewingInline={false}
                            activeJobId={activeJob?.id}
                            onSelect={setSelectedRunId}
                        />

                        {activeRun ? (
                            <div className="flex flex-col gap-4 min-w-0">
                                {activeRun.stages.map((st) => (
                                    <div
                                        key={st.stage_id}
                                        className="voxel-trough bg-voxel-trough p-4 flex flex-col gap-3 min-w-0"
                                    >
                                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-voxel-bevel-lo pb-2">
                                            <span className="text-sm font-bold text-voxel-ink">
                                                LLM Call
                                            </span>
                                            <span className="text-xs font-normal font-mono text-voxel-muted">
                                                {activeRun.signals.length > 0
                                                    ? activeRun.signals
                                                          .map((s) => `${s.action} ${s.ticker}`)
                                                          .join(', ')
                                                    : 'HOLD'}
                                            </span>
                                        </div>
                                        <TraceInspectorBlock
                                            prompt={st.prompt}
                                            trace={st.trace}
                                            toolCalls={st.tool_calls}
                                            fullOutput={st.output}
                                        />
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="voxel-trough bg-voxel-trough p-4">
                                <span className="text-xs font-normal text-voxel-muted">
                                    Selected live job has no trace output yet (status:{' '}
                                    {activeJob?.status ?? 'pending'}).
                                </span>
                            </div>
                        )}
                    </Card>
                )}

                {!hasPortfolio && !hasRuns && (
                    <div className="voxel-trough bg-voxel-trough p-6 text-center">
                        <span className="text-xs font-normal text-voxel-muted">
                            No live runs yet. The first scheduled run will execute at the next
                            3x/day ET slot (09:30, 12:30, 15:30).
                        </span>
                    </div>
                )}
            </div>
        </PageLayout>
    );
}
