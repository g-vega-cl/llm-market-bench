import { Badge, Button, PageLayout } from '@llm-market-bench/ui-design-system';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { fetchRecipeQuotaStatusFn, toggleLiveScheduleFn } from '../api/recipes-quota-api';
import {
    fetchLivePortfolioAndRunsFn,
    fetchRecipeAlertsFn,
    markAlertReadFn,
    previewStrategyPromptFn,
    submitWaitlistPledgeFn,
} from '../api/recipes-studio-api';
import { LiveRunsBlock } from '../components/LiveRunsBlock';
import { PromptVisualizer } from '../components/PromptVisualizer';
import { RecipeAlertsInbox } from '../components/RecipeAlertsInbox';
import {
    RecentBacktestsStrip,
    RecipeGuideAndQuotaBlock,
    resolveBacktestButtonLabel,
    SavedRecipesStrip,
    StudioAlertSlot,
} from '../components/RecipeGuideAndQuotaBlock';
import { StageBuilder } from '../components/StageBuilder';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import { STARTER_RECIPES } from '../starter-templates';
import type {
    BacktestResultData,
    ExecutionState,
    LivePortfolioAndRuns,
    LiveRunResult,
    PreviewState,
    PushStrategy,
    RecipeAlert,
    RecipeJobRecord,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
    StrategyRecipeRecord,
    StrategyStage,
} from '../types';
import {
    buildExecutionErrorState,
    buildInlinePortfolio,
    isQuotaLimitMessage,
    pollJobResults,
    resolvePreviousBacktestJobId,
    upsertSavedRecipeSummary,
} from '../utils/live-studio-helpers';

interface RecipeStudioPageProps {
    initialStrategy?: PushStrategy | null;
    recentBacktests?: RecipeJobRecord[];
    initialLiveState?: LivePortfolioAndRuns | null;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
}

export function RecipeStudioPage({
    initialStrategy = null,
    recentBacktests = [],
    initialLiveState = null,
    initialQuota = null,
    initialUserRecipes = [],
}: RecipeStudioPageProps = {}) {
    const navigate = useNavigate();
    const [strategy, setStrategy] = useState<PushStrategy>(
        () => initialStrategy ?? STARTER_RECIPES[0],
    );
    const [activeTemplateIdx, setActiveTemplateIdx] = useState<number>(() =>
        initialStrategy ? -1 : 0,
    );

    const [execution, setExecution] = useState<ExecutionState>({ status: 'idle' });
    const [scheduleError, setScheduleError] = useState<string | null>(null);
    const [preview, setPreview] = useState<PreviewState>({ status: 'template' });
    const [liveState, setLiveState] = useState<LivePortfolioAndRuns | null>(initialLiveState);
    const [quotaStatus, setQuotaStatus] = useState<RecipeUserQuotaStatus | null>(initialQuota);
    const [userRecipes, setUserRecipes] = useState<RecipeSummaryItem[]>(initialUserRecipes);
    const [isTogglingLive, setIsTogglingLive] = useState(false);

    const [alerts, setAlerts] = useState<RecipeAlert[]>([]);
    const [showAlertsInbox, setShowAlertsInbox] = useState<boolean>(false);
    const [showPledgeModal, setShowPledgeModal] = useState<boolean>(false);

    const refreshQuota = async () => {
        try {
            const nextQuota = await fetchRecipeQuotaStatusFn();
            if (nextQuota) setQuotaStatus(nextQuota);
        } catch {
            // Non-blocking UI refresh
        }
    };

    const handleSelectTemplate = (idx: number) => {
        setActiveTemplateIdx(idx);
        setStrategy(STARTER_RECIPES[idx]);
        setExecution({ status: 'idle' });
        setScheduleError(null);
        setPreview({ status: 'template' });
        setLiveState(null);
    };

    const handleStageChange = (updated: StrategyStage) => {
        setStrategy((prev) => ({ ...prev, stages: [updated] }));
        setPreview({ status: 'template' });
    };

    const handlePreviewLiveData = async () => {
        setPreview({ status: 'loading' });
        try {
            const hydratedByBlockId = await previewStrategyPromptFn({ data: { strategy } });
            setPreview({ status: 'hydrated', hydratedByBlockId });
        } catch (err) {
            setPreview({
                status: 'error',
                message: err instanceof Error ? err.message : 'Failed to preview live data',
            });
        }
    };

    const applyCompletedLiveRun = async (recipeId: string, result: LiveRunResult) => {
        setExecution({ status: 'live_done', result });
        const optimisticPortfolio = buildInlinePortfolio(result);
        if (optimisticPortfolio) {
            setLiveState((prev) => ({
                portfolio: optimisticPortfolio,
                recentLiveRuns: prev?.recentLiveRuns ?? [],
            }));
        }
        const refreshed = await fetchLivePortfolioAndRunsFn({
            data: { recipeId },
        }).catch(() => null);
        if (refreshed) setLiveState(refreshed);
    };

    const persistActiveStrategy = async (): Promise<StrategyRecipeRecord> => {
        const saved = (await saveRecipeFn({ data: { recipe: strategy } })) as StrategyRecipeRecord;
        setStrategy((prev) => (prev.id === saved.id ? prev : { ...prev, id: saved.id }));
        setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved));
        return saved;
    };

    const settleLiveExecution = async (
        recipeId: string,
        job: { id: string; result_json?: LiveRunResult | BacktestResultData },
    ) => {
        if (job.result_json) {
            await applyCompletedLiveRun(recipeId, job.result_json as LiveRunResult);
            return;
        }
        const finalState = await pollJobResults(job.id);
        if (finalState.status === 'live_done') {
            await applyCompletedLiveRun(recipeId, finalState.result);
            return;
        }
        setExecution(finalState);
    };

    const handleExecute = async (mode: 'live_turn' | 'backtest') => {
        if (isBusy) return;
        const prevBacktestJobId = resolvePreviousBacktestJobId(execution);
        setExecution({ status: 'running', mode });
        setScheduleError(null);
        let queuedBacktestJobId: string | undefined;
        let didNavigate = false;
        try {
            const saved = await persistActiveStrategy();
            const job = (await enqueueRecipeJobFn({
                data: { recipeId: saved.id, mode },
            })) as { id: string; status: string; result_json?: LiveRunResult | BacktestResultData };

            if (mode === 'backtest') {
                queuedBacktestJobId = job.id;
                await navigate({ to: '/recipes/backtest/$jobId', params: { jobId: job.id } });
                didNavigate = true;
                return;
            }

            await settleLiveExecution(saved.id, job);
        } catch (err) {
            setExecution(
                buildExecutionErrorState({
                    err,
                    mode,
                    queuedBacktestJobId,
                    prevBacktestJobId,
                }),
            );
        } finally {
            if (!didNavigate) await refreshQuota();
        }
    };

    const currentSavedRecord = userRecipes.find((r) => r.id === strategy.id);
    const isCurrentlyScheduledLive = Boolean(currentSavedRecord?.is_live);

    const handleToggleScheduledLive = async () => {
        if (isBusy) return;
        setIsTogglingLive(true);
        setScheduleError(null);
        if (execution.status === 'error') {
            setExecution({ status: 'idle' });
        }
        try {
            const saved = await persistActiveStrategy();
            const updated = await toggleLiveScheduleFn({
                data: { recipeId: saved.id, isLive: !isCurrentlyScheduledLive },
            });
            setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved, updated.is_live));
        } catch (err) {
            const message =
                err instanceof Error ? err.message : 'Failed updating Scheduled Live status';
            if (isQuotaLimitMessage(message)) {
                console.warn('[RecipeStudio] Scheduled Live blocked by quota:', message);
            } else {
                console.error('[RecipeStudio] Failed updating Scheduled Live status:', err);
            }
            setScheduleError(message);
        } finally {
            setIsTogglingLive(false);
            await refreshQuota();
        }
    };

    const handleLoadAlerts = async () => {
        try {
            const list = await fetchRecipeAlertsFn();
            setAlerts(list);
        } finally {
            setShowAlertsInbox(true);
        }
    };

    const handleMarkAlertRead = async (alertId: string) => {
        await markAlertReadFn({ data: { alertId } });
        setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, is_read: true } : a)));
    };

    const handlePledgeSubmit = async (email: string, tier: string, feedback: string) => {
        await submitWaitlistPledgeFn({
            data: { email, intendedTier: tier, feedback },
        });
    };

    const isRunning = execution.status === 'running';
    const isBusy = isRunning || isTogglingLive;
    const backtestButtonLabel = resolveBacktestButtonLabel(
        isRunning && execution.mode === 'backtest',
        quotaStatus,
    );

    return (
        <PageLayout>
            <div className="flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
                    <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                            <h1 className="font-display text-lg font-bold text-foreground">
                                Strategy Builder MVP
                            </h1>
                            <Badge variant="outline" size="sm">
                                5-Block Push v2
                            </Badge>
                        </div>
                        <p className="text-xs font-normal text-muted-foreground">
                            Compose Prompt, News, Memories, Technicals, and Output Format blocks
                            into a single Long-Only LLM call (runs 3x/day ET at 09:30, 12:30,
                            15:30).
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowPledgeModal(true)}
                        >
                            ★ Waitlist
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleLoadAlerts}>
                            Alerts ({alerts.filter((a) => !a.is_read).length})
                        </Button>
                        <Button
                            size="sm"
                            variant={isCurrentlyScheduledLive ? 'solid' : 'outline'}
                            colorScheme={isCurrentlyScheduledLive ? 'success' : 'neutral'}
                            onClick={handleToggleScheduledLive}
                            disabled={isBusy}
                            isLoading={isTogglingLive}
                        >
                            {isCurrentlyScheduledLive
                                ? 'Scheduled Live: ON (3x/d)'
                                : 'Schedule Live (3x/d)'}
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleExecute('live_turn')}
                            disabled={isBusy}
                        >
                            {isRunning && execution.mode === 'live_turn'
                                ? 'Running Live...'
                                : '▶ Run Live'}
                        </Button>
                        <Button
                            size="sm"
                            variant="solid"
                            onClick={() => handleExecute('backtest')}
                            disabled={isBusy}
                            isLoading={isRunning && execution.mode === 'backtest'}
                        >
                            {backtestButtonLabel}
                        </Button>
                    </div>
                </div>

                <StudioAlertSlot
                    execution={execution}
                    scheduleError={scheduleError}
                    onRequestCapacity={() => setShowPledgeModal(true)}
                />

                <RecipeGuideAndQuotaBlock quotaStatus={quotaStatus} />

                <SavedRecipesStrip recipes={userRecipes} activeRecipeId={strategy.id} />

                <RecentBacktestsStrip recentBacktests={recentBacktests} />

                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-muted-foreground">Templates:</span>
                        {STARTER_RECIPES.map((tmpl, idx) => (
                            <Button
                                key={tmpl.name}
                                size="sm"
                                variant={activeTemplateIdx === idx ? 'solid' : 'outline'}
                                onClick={() => handleSelectTemplate(idx)}
                                disabled={isBusy}
                            >
                                {tmpl.name}
                            </Button>
                        ))}
                    </div>
                </div>

                <div className="flex flex-col gap-4">
                    <StageBuilder stage={strategy.stages[0]} onChange={handleStageChange} />
                    <PromptVisualizer
                        stage={strategy.stages[0]}
                        previewState={preview}
                        onPreviewLiveData={handlePreviewLiveData}
                    />
                </div>

                <LiveRunsBlock
                    portfolio={liveState?.portfolio ?? null}
                    recentLiveRuns={liveState?.recentLiveRuns ?? []}
                    latestInlineRun={execution.status === 'live_done' ? execution.result : null}
                />

                {showAlertsInbox && (
                    <RecipeAlertsInbox
                        alerts={alerts}
                        onClose={() => setShowAlertsInbox(false)}
                        onMarkRead={handleMarkAlertRead}
                    />
                )}

                <WaitlistPledgeModal
                    isOpen={showPledgeModal}
                    onClose={() => setShowPledgeModal(false)}
                    onSubmit={handlePledgeSubmit}
                />
            </div>
        </PageLayout>
    );
}
