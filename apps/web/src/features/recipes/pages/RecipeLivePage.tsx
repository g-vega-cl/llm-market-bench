import {
    Badge,
    Button,
    Card,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { formatEasternDateTime } from '~/utils/date';
import { activateRecipeTurboFn } from '../api/recipes-quota-api';
import { RecipePortfolioBlock } from '../components/RecipePortfolioBlock';
import { TraceInspectorBlock } from '../components/TraceInspectorBlock';
import { TurboButton } from '../components/TurboButton';
import type {
    LivePortfolioSnapshot,
    LiveRunResult,
    LiveStatusMeta,
    RecipeJobRecord,
} from '../types';
import { formatTurboRemainingLabel, getNextLiveSlotLabel } from '../utils/market-hours';

const INLINE_LATEST_ID = 'inline-latest';

interface RecipeLivePageProps {
    recipeId: string;
    initialData: {
        portfolio: LivePortfolioSnapshot;
        recentLiveRuns: RecipeJobRecord[];
        liveMeta?: LiveStatusMeta;
    } | null;
}

function extractLiveResult(job: RecipeJobRecord | undefined): LiveRunResult | null {
    if (!job?.result_json) return null;
    if ('mode' in job.result_json && job.result_json.mode === 'live_turn') {
        return job.result_json as LiveRunResult;
    }
    return null;
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
                const stamp = run.created_at ? formatEasternDateTime(run.created_at) : '';
                const label = stamp && stamp !== 'Unknown' ? stamp : run.id.slice(0, 8);
                return (
                    <Button
                        key={run.id}
                        size="sm"
                        variant={isSelected ? 'solid' : 'outline'}
                        onClick={() => onSelect(run.id)}
                    >
                        {label}
                    </Button>
                );
            })}
        </div>
    );
}

interface LiveStatusHeaderProps {
    recipeId: string;
    isLiveEnabled: boolean;
    turboRemaining: string | null;
    nextSlotLabel: string;
    liveMeta?: LiveStatusMeta;
    turboExpiresAt: string | null;
    turboUsedToday: boolean;
    isActivatingTurbo: boolean;
    now: Date;
    onActivateTurbo: () => void;
}

function LiveStatusHeader({
    recipeId,
    isLiveEnabled,
    turboRemaining,
    nextSlotLabel,
    liveMeta,
    turboExpiresAt,
    turboUsedToday,
    isActivatingTurbo,
    now,
    onActivateTurbo,
}: LiveStatusHeaderProps) {
    return (
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-4">
            <div className="flex items-center gap-3">
                <Link
                    to="/build"
                    search={{ recipeId }}
                    className="voxel-btn inline-flex items-center gap-2 px-3 py-1.5 text-sm font-bold border border-voxel-bevel-hi bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated rounded-none"
                >
                    ← Edit Bot
                </Link>
                <div>
                    <h1 className="type-heading text-voxel-ink">Live Status</h1>
                    <span className="type-body text-voxel-muted">
                        Recipe ID: {recipeId.slice(0, 8)}
                    </span>
                </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
                {!isLiveEnabled ? (
                    <Badge variant="soft" colorScheme="neutral" size="sm">
                        Live: PAUSED
                    </Badge>
                ) : turboRemaining ? (
                    <Badge variant="solid" colorScheme="accent" size="sm" suppressHydrationWarning>
                        Turbo: {turboRemaining} (5m)
                    </Badge>
                ) : (
                    <Badge variant="soft" colorScheme="success" size="sm">
                        Live: ON (30m)
                    </Badge>
                )}
                <span className="type-body text-voxel-muted" suppressHydrationWarning>
                    {!isLiveEnabled
                        ? 'Next run: Paused'
                        : `Next run: ${turboRemaining ? 'within 5m (Turbo)' : nextSlotLabel}`}
                </span>
                {liveMeta?.isOwner && liveMeta?.isLive && (
                    <TurboButton
                        turboExpiresAt={turboExpiresAt}
                        turboUsedToday={turboUsedToday}
                        isActivating={isActivatingTurbo}
                        now={now}
                        onActivate={onActivateTurbo}
                    />
                )}
            </div>
        </div>
    );
}

export function RecipeLivePage({ recipeId, initialData }: RecipeLivePageProps) {
    const [selectedRunId, setSelectedRunId] = useState<string | null>(
        () => initialData?.recentLiveRuns[0]?.id ?? null,
    );
    const [turboExpiresAt, setTurboExpiresAt] = useState<string | null>(
        () => initialData?.liveMeta?.turboExpiresAt ?? null,
    );
    const [turboUsedToday, setTurboUsedToday] = useState<boolean>(
        () => initialData?.liveMeta?.turboUsedToday ?? false,
    );
    const [isActivatingTurbo, setIsActivatingTurbo] = useState(false);
    const [turboError, setTurboError] = useState<string | null>(null);
    const [now, setNow] = useState<Date>(() => new Date());

    useEffect(() => {
        const timer = setInterval(() => setNow(new Date()), 15_000);
        return () => clearInterval(timer);
    }, []);

    const recentLiveRuns = initialData?.recentLiveRuns ?? [];
    const portfolio = initialData?.portfolio ?? null;
    const liveMeta = initialData?.liveMeta;
    const isLiveEnabled = liveMeta ? liveMeta.isLive : true;

    const activeSelection = selectedRunId ?? recentLiveRuns[0]?.id ?? null;
    const activeJob = recentLiveRuns.find((run) => run.id === activeSelection) ?? recentLiveRuns[0];
    const activeRun = extractLiveResult(activeJob);

    const hasPortfolio = portfolio !== null;
    const hasRuns = recentLiveRuns.length > 0;

    const nextSlotLabel = getNextLiveSlotLabel(now);
    const turboRemaining = isLiveEnabled ? formatTurboRemainingLabel(turboExpiresAt, now) : null;

    const handleActivateTurbo = async () => {
        if (isActivatingTurbo) return;
        setIsActivatingTurbo(true);
        setTurboError(null);
        try {
            const res = await activateRecipeTurboFn({ data: { recipeId } });
            setTurboExpiresAt(res.turboExpiresAt);
            setTurboUsedToday(true);
        } catch (err) {
            setTurboError(err instanceof Error ? err.message : 'Failed activating Turbo mode');
        } finally {
            setIsActivatingTurbo(false);
        }
    };

    return (
        <PageLayout>
            <div className="flex flex-col gap-6">
                <LiveStatusHeader
                    recipeId={recipeId}
                    isLiveEnabled={isLiveEnabled}
                    turboRemaining={turboRemaining}
                    nextSlotLabel={nextSlotLabel}
                    liveMeta={liveMeta}
                    turboExpiresAt={turboExpiresAt}
                    turboUsedToday={turboUsedToday}
                    isActivatingTurbo={isActivatingTurbo}
                    now={now}
                    onActivateTurbo={handleActivateTurbo}
                />

                {turboError && (
                    <div
                        role="alert"
                        className="border border-danger bg-voxel-surface p-3 text-xs font-normal text-danger rounded-none"
                    >
                        {turboError}
                    </div>
                )}

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
                                    $10,000 live paper ledger (every 30m during market hours
                                    09:30–16:00 ET, or every 5m while Turbo is active).
                                </span>
                            </div>
                            {activeRun && (
                                <div className="flex flex-wrap items-center gap-2">
                                    <Badge variant="soft" size="xs">
                                        {activeRun.slot_label ||
                                            formatEasternDateTime(activeRun.as_of_utc)}
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
                            30-minute market-hours ET slot (09:30–16:00 ET).
                        </span>
                    </div>
                )}
            </div>
        </PageLayout>
    );
}
