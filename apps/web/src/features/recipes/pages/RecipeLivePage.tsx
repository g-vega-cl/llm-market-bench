import {
    type AtmospherePhase,
    Badge,
    Card,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import { formatEasternDateTime } from '~/utils/date';
import { activateRecipeTurboFn } from '../api/recipes-quota-api';
import { BotStageHeader } from '../components/BotStageHeader';
import { ClosedTradesSection } from '../components/ClosedTradesSection';
import { RecipePortfolioBlock } from '../components/RecipePortfolioBlock';
import { RunPaginator } from '../components/RunPaginator';
import { TraceInspectorBlock } from '../components/TraceInspectorBlock';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import type {
    LivePortfolioSnapshot,
    LiveRunResult,
    LiveStatusMeta,
    RecipeCadence,
    RecipeJobRecord,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
} from '../types';
import { extractLiveRunResult } from '../utils/recipe-insights';
import { useBotHeaderActions } from '../utils/use-bot-header-actions';

interface RecipeLivePageProps {
    recipeId: string;
    initialData: {
        portfolio: LivePortfolioSnapshot;
        recentLiveRuns: RecipeJobRecord[];
        liveMeta?: LiveStatusMeta;
    } | null;
    cadence?: RecipeCadence;
    initialAtmosphere?: AtmospherePhase;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
}

/**
 * Eastern-time stamp that names a run. The daemon's slot label is already in ET,
 * but it reads as a raw ISO slice, so every surface formats `as_of_utc` instead
 * and falls back to the job's `created_at` when a run never produced a result.
 */
function runStampLabel(job: RecipeJobRecord | undefined, run: LiveRunResult | null): string {
    const iso = run?.as_of_utc ?? job?.created_at;
    const stamp = formatEasternDateTime(iso);
    if (stamp && stamp !== 'Unknown') return stamp;
    return job?.id.slice(0, 8) ?? 'Unknown';
}

function LiveRunTracesSection({
    recentLiveRuns,
    runPage,
    onChangePage,
}: {
    recentLiveRuns: RecipeJobRecord[];
    runPage: number;
    onChangePage: (next: number) => void;
}) {
    if (recentLiveRuns.length === 0) {
        return (
            <Card padding="md" className="flex flex-col gap-2">
                <SectionHeading>Live Run Traces</SectionHeading>
                <div className="voxel-trough bg-voxel-trough p-4">
                    <span className="text-xs font-normal text-voxel-muted">
                        No live runs yet. The first scheduled run will execute at the next 30-minute
                        market-hours ET slot (09:30–16:00 ET).
                    </span>
                </div>
            </Card>
        );
    }

    const totalRuns = recentLiveRuns.length;
    const runPageIndex = Math.min(runPage, totalRuns - 1);
    const activeJob = recentLiveRuns[runPageIndex];
    const activeRun = extractLiveRunResult(activeJob);
    const activeStamp = runStampLabel(activeJob, activeRun);

    return (
        <Card padding="md" className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-3">
                <div className="flex flex-col gap-1 min-w-0">
                    <SectionHeading>Live Run Traces</SectionHeading>
                    <span className="text-xs font-normal text-voxel-muted">
                        Runs independently on clvg.uk auto-go against your isolated $10,000 live
                        paper ledger (every 30m during market hours 09:30–16:00 ET, or every 5m
                        while Turbo is active).
                    </span>
                </div>
                {activeRun ? (
                    <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="soft" size="xs">
                            {activeStamp}
                        </Badge>
                        <Badge variant="soft" colorScheme="accent" size="xs">
                            {activeRun.signals.length} Signals
                        </Badge>
                    </div>
                ) : null}
            </div>

            <RunPaginator
                index={runPageIndex}
                total={totalRuns}
                onOlder={() => onChangePage(runPageIndex + 1)}
                onNewer={() => onChangePage(Math.max(runPageIndex - 1, 0))}
            />

            {activeRun ? (
                <div className="flex flex-col gap-4 min-w-0">
                    {activeRun.stages.map((st) => (
                        <div
                            key={st.stage_id}
                            className="voxel-trough bg-voxel-trough p-4 flex flex-col gap-3 min-w-0"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-voxel-bevel-lo pb-2">
                                <span className="text-sm font-bold text-voxel-ink">LLM Call</span>
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
                        {activeStamp} ·{' '}
                        {activeJob?.status === 'failed'
                            ? 'failed — no trace output'
                            : `no trace output yet (status: ${activeJob?.status ?? 'pending'}).`}
                    </span>
                    {activeJob?.error_message ? (
                        <p className="text-xs font-normal text-danger break-words">
                            {activeJob.error_message}
                        </p>
                    ) : null}
                </div>
            )}
        </Card>
    );
}

export function RecipeLivePage({
    recipeId,
    initialData,
    cadence = '3h',
    initialAtmosphere,
    initialQuota = null,
    initialUserRecipes = [],
}: RecipeLivePageProps) {
    const [runPage, setRunPage] = useState(0);
    const [turboExpiresAt, setTurboExpiresAt] = useState<string | null>(
        () => initialData?.liveMeta?.turboExpiresAt ?? null,
    );
    const [turboUsedToday, setTurboUsedToday] = useState<boolean>(
        () => initialData?.liveMeta?.turboUsedToday ?? false,
    );
    const [isActivatingTurbo, setIsActivatingTurbo] = useState(false);
    const [turboError, setTurboError] = useState<string | null>(null);

    const recentLiveRuns = initialData?.recentLiveRuns ?? [];
    const portfolio = initialData?.portfolio ?? null;
    const liveMeta = initialData?.liveMeta;
    const isLiveEnabled = liveMeta ? liveMeta.isLive : true;

    const actions = useBotHeaderActions({
        recipeId,
        recipeName: liveMeta?.recipeName || `Recipe ${recipeId.slice(0, 8)}`,
        cadence: liveMeta?.cadence ?? cadence,
        initialIsLive: isLiveEnabled,
        initialQuota,
        initialUserRecipes,
    });

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

    const isOwner = liveMeta?.isOwner ?? false;
    const conflictingLiveRecipe =
        actions.liveControl.state.kind === 'confirming' ||
        actions.liveControl.state.kind === 'switching'
            ? actions.liveControl.state.conflicting
            : null;

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink flex flex-col">
            <BotStageHeader
                recipeId={recipeId}
                recipeName={liveMeta?.recipeName || `Live Runs · ${recipeId.slice(0, 8)}`}
                description={liveMeta?.description}
                cadence={liveMeta?.cadence ?? cadence}
                activeTab="live"
                isOwner={isOwner}
                isPublic={liveMeta?.isPublic}
                isTemplate={liveMeta?.isTemplate}
                isLive={actions.isLive}
                turboExpiresAt={turboExpiresAt}
                turboUsedToday={turboUsedToday}
                initialAtmosphere={initialAtmosphere}
                quotaStatus={actions.quotaStatus}
                isRunningBacktest={actions.isRunningBacktest}
                isTogglingLive={actions.liveControl.isBusy}
                isActivatingTurbo={isActivatingTurbo}
                isForking={actions.isForking}
                backtestError={actions.backtestError}
                scheduleError={actions.liveControl.scheduleError}
                forkError={actions.forkError}
                turboError={turboError}
                conflictingLiveRecipe={conflictingLiveRecipe}
                isSwitchingLive={actions.liveControl.state.kind === 'switching'}
                onBacktest={isOwner ? actions.handleBacktest : undefined}
                onToggleLive={isOwner ? actions.handleToggleLive : undefined}
                onConfirmLiveSwitch={actions.handleConfirmSwitch}
                onCancelLiveSwitch={actions.liveControl.cancelSwitch}
                onActivateTurbo={isOwner ? handleActivateTurbo : undefined}
                onFork={!isOwner ? actions.handleFork : undefined}
                onRequestCapacity={() => actions.setShowPledgeModal(true)}
            />

            <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                <LiveRunTracesSection
                    recentLiveRuns={recentLiveRuns}
                    runPage={runPage}
                    onChangePage={setRunPage}
                />

                {portfolio ? (
                    <Card padding="md" className="flex flex-col gap-6 min-w-0">
                        <RecipePortfolioBlock
                            title="Live Paper Portfolio"
                            cash={portfolio.cash}
                            totalEquity={portfolio.total_equity}
                            openPositions={portfolio.open_positions}
                            embedded
                        />
                        <ClosedTradesSection
                            title="All Closed Live Trades"
                            trades={portfolio.trades}
                            emptyMessage="No closed live trades recorded yet."
                        />
                    </Card>
                ) : null}

                <WaitlistPledgeModal
                    isOpen={actions.showPledgeModal}
                    onClose={() => actions.setShowPledgeModal(false)}
                    onSubmit={actions.handlePledgeSubmit}
                />
            </PageLayout>
        </div>
    );
}
