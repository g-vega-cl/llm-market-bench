import { Badge, Button, PageLayout } from '@llm-market-bench/ui-design-system';
import { Link, useNavigate } from '@tanstack/react-router';
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
    RecipeGuideAndQuotaBlock,
    SavedRecipesStrip,
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
    buildInlinePortfolio,
    pollJobResults,
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

    const handleExecute = async (mode: 'live_turn' | 'backtest') => {
        setExecution({ status: 'running', mode });
        try {
            const saved = (await saveRecipeFn({
                data: { recipe: strategy },
            })) as StrategyRecipeRecord;
            setStrategy((prev) => (prev.id === saved.id ? prev : { ...prev, id: saved.id }));
            setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved));
            const job = (await enqueueRecipeJobFn({
                data: {
                    recipeId: saved.id,
                    mode,
                },
            })) as {
                id: string;
                status: string;
                result_json?: LiveRunResult | BacktestResultData;
            };

            if (mode === 'backtest') {
                await navigate({
                    to: '/recipes/backtest/$jobId',
                    params: { jobId: job.id },
                });
                return;
            }

            if (job.result_json) {
                await applyCompletedLiveRun(saved.id, job.result_json as LiveRunResult);
                return;
            }
            const finalState = await pollJobResults(job.id);
            if (finalState.status === 'live_done') {
                await applyCompletedLiveRun(saved.id, finalState.result);
                return;
            }
            setExecution(finalState);
        } catch (err) {
            setExecution({
                status: 'error',
                message: err instanceof Error ? err.message : 'Execution failed',
            });
        } finally {
            await refreshQuota();
        }
    };

    const currentSavedRecord = userRecipes.find((r) => r.id === strategy.id);
    const isCurrentlyScheduledLive = Boolean(currentSavedRecord?.is_live);

    const handleToggleScheduledLive = async () => {
        if (isTogglingLive) return;
        setIsTogglingLive(true);
        try {
            const saved = (await saveRecipeFn({
                data: { recipe: strategy },
            })) as StrategyRecipeRecord;
            setStrategy((prev) => (prev.id === saved.id ? prev : { ...prev, id: saved.id }));
            const updated = await toggleLiveScheduleFn({
                data: { recipeId: saved.id, isLive: !isCurrentlyScheduledLive },
            });
            setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved, updated.is_live));
        } catch (err) {
            setExecution({
                status: 'error',
                message:
                    err instanceof Error ? err.message : 'Failed updating Scheduled Live status',
            });
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
                            disabled={isRunning}
                        >
                            {isRunning && execution.mode === 'live_turn'
                                ? 'Running Live...'
                                : '▶ Run Live'}
                        </Button>
                        <Button
                            size="sm"
                            variant="solid"
                            onClick={() => handleExecute('backtest')}
                            disabled={isRunning}
                            isLoading={isRunning && execution.mode === 'backtest'}
                        >
                            {isRunning && execution.mode === 'backtest'
                                ? 'Starting Backtest...'
                                : '▶ Backtest (Random 2W)'}
                        </Button>
                    </div>
                </div>

                <RecipeGuideAndQuotaBlock quotaStatus={quotaStatus} />

                <SavedRecipesStrip recipes={userRecipes} activeRecipeId={strategy.id} />

                {recentBacktests.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 voxel-trough bg-boxel-trough p-3">
                        <span className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                            Recent Backtests:
                        </span>
                        {recentBacktests.slice(0, 5).map((run) => {
                            const bt =
                                run.result_json &&
                                (!('mode' in run.result_json) ||
                                    run.result_json.mode !== 'live_turn')
                                    ? (run.result_json as BacktestResultData)
                                    : null;
                            const label =
                                run.status === 'completed' &&
                                bt &&
                                typeof bt.total_return_pct_net === 'number'
                                    ? `${bt.total_return_pct_net >= 0 ? '+' : ''}${bt.total_return_pct_net.toFixed(2)}%`
                                    : `${run.status.toUpperCase()} (${run.progress_pct}%)`;
                            return (
                                <Link
                                    key={run.id}
                                    to="/recipes/backtest/$jobId"
                                    params={{ jobId: run.id }}
                                    className="voxel-btn inline-flex items-center gap-2 px-2 py-1 text-xs font-mono border border-boxel-bevel-hi bg-boxel-surface text-boxel-ink hover:bg-boxel-elevated rounded-none"
                                >
                                    <span>{run.id.slice(0, 8)}</span>
                                    <span className="text-accent">{label}</span>
                                </Link>
                            );
                        })}
                    </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-muted-foreground">Templates:</span>
                        {STARTER_RECIPES.map((tmpl, idx) => (
                            <Button
                                key={tmpl.name}
                                size="sm"
                                variant={activeTemplateIdx === idx ? 'solid' : 'outline'}
                                onClick={() => handleSelectTemplate(idx)}
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

                {execution.status === 'error' && (
                    <div className="border border-destructive bg-boxel-surface p-3 text-xs font-normal text-destructive rounded-none">
                        {execution.message}
                    </div>
                )}

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
