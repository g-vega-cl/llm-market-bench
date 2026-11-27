import { Button, PageLayout } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { track } from '~/lib/analytics';
import { assertServerFnResult } from '~/lib/server-fn';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { fetchRecipeQuotaStatusFn } from '../api/recipes-quota-api';
import { previewStrategyPromptFn, submitWaitlistPledgeFn } from '../api/recipes-studio-api';
import { DataCoverageNote } from '../components/DataCoverageNote';
import { LiveSwitchConfirmation } from '../components/LiveSwitchConfirmation';
import {
    resolveBacktestButtonLabel,
    StudioAlertSlot,
} from '../components/RecipeGuideAndQuotaBlock';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import type {
    BacktestError,
    BacktestResultData,
    PreviewState,
    PushStrategy,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
    StrategyRecipeRecord,
    StrategyStage,
} from '../types';
import { buildBacktestError, upsertSavedRecipeSummary } from '../utils/live-studio-helpers';
import { useLatestRecipeRun } from '../utils/use-latest-recipe-run';
import { useLiveScheduleControl } from '../utils/use-live-schedule-control';
import { useRecipeDraft } from '../utils/use-recipe-draft';
import { useRecipeLiveSummary } from '../utils/use-recipe-live-summary';
import { BuilderBotLiveStatus } from './BuilderBotLiveStatus';
import { BuilderStatusStrip } from './BuilderStatusStrip';
import { BuilderStepper } from './BuilderStepper';
import { CompiledBotBlueprintSection, type WorkspaceTab } from './CompiledBotBlueprintSection';
import { CompiledBotSummaryCard } from './CompiledBotSummaryCard';
import {
    deriveWorkspaceStatus,
    describeRun,
    isInFlightRun,
    LiveWarningBanner,
    resolveLiveWarningMessage,
    resolveScheduledLive,
} from './compiled-bot-status';
import type { RecipeLiveSummary } from './live-summary';

export interface CompiledBotWorkspaceProps {
    initialStrategy: PushStrategy;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
    /** Live facts cut from the live page's read; null when unknown. */
    initialLive?: RecipeLiveSummary | null;
    summary?: string;
    fallback?: boolean;
    warning?: string;
    onStartOver?: () => void;
}

/**
 * Step 2 of `/build` (and `/build?recipeId=<id>`):
 * Block 1 renders the bot identity, status strip, and primary CTAs inside a
 * `.voxel-card` header; Block 2 renders the calm blueprint workspace below with
 * a segmented tab switcher (`Blocks & Tools` | `Prompt Preview`).
 */
export function CompiledBotWorkspace({
    initialStrategy,
    initialQuota = null,
    initialUserRecipes = [],
    initialLive = null,
    summary,
    fallback = false,
    warning,
    onStartOver,
}: CompiledBotWorkspaceProps) {
    const navigate = useNavigate();
    const posthog = usePostHog();

    const draft = useRecipeDraft(initialStrategy, initialStrategy.id ? initialStrategy.name : null);
    const strategy = draft.strategy;
    const stage = strategy.stages[0];
    const { run } = useLatestRecipeRun(strategy.id);
    const runView = describeRun(run);
    const runInFlight = isInFlightRun(run);
    const draftNote = draft.isDirty
        ? 'Draft not saved yet — Save Recipe persists it before any run.'
        : 'Saved.';
    const statusDetail = [
        runInFlight ? runView?.text : draftNote,
        runInFlight ? draftNote : runView?.text,
    ]
        .filter(Boolean)
        .join(' · ');

    const [quotaStatus, setQuotaStatus] = useState<RecipeUserQuotaStatus | null>(initialQuota);
    const [userRecipes, setUserRecipes] = useState<RecipeSummaryItem[]>(initialUserRecipes);
    const [preview, setPreview] = useState<PreviewState>({ status: 'template' });
    const [isRunningBacktest, setIsRunningBacktest] = useState(false);
    const [backtestError, setBacktestError] = useState<BacktestError | null>(null);
    const [showPledgeModal, setShowPledgeModal] = useState(false);
    const [activeTab, setActiveTab] = useState<WorkspaceTab>('blocks');

    const liveSummary: RecipeLiveSummary | null = useRecipeLiveSummary(strategy.id, initialLive);

    const currentSavedRecord = userRecipes.find((r) => r.id === strategy.id);
    // Tri-state: `null` when neither the summary nor the capped My Bots list knows.
    const isCurrentlyScheduledLive = resolveScheduledLive({
        recipeId: strategy.id,
        live: liveSummary,
        loadedRecipes: initialUserRecipes,
        currentRecipes: userRecipes,
    });

    const refreshQuota = async () => {
        try {
            const next = await fetchRecipeQuotaStatusFn();
            if (next) setQuotaStatus(next);
        } catch {
            // Non-blocking refresh
        }
    };

    const liveControl = useLiveScheduleControl({
        userRecipes,
        quotaStatus,
        onRecipesChange: setUserRecipes,
        onRefreshQuota: refreshQuota,
        onEnabledNavigate: async (recipeId) => {
            await navigate({ to: '/recipes/live/$recipeId/runs', params: { recipeId } });
        },
    });

    const isBusy = draft.isSaving || isRunningBacktest || liveControl.isBusy;
    const promptBlock = stage.blocks.find((block) => block.type === 'prompt');
    const hasEmptyPrompt = !promptBlock?.text.trim();
    const liveWarningMessage = resolveLiveWarningMessage(warning, stage.selected_tools);
    const workspaceStatus = deriveWorkspaceStatus({
        hasEmptyPrompt,
        runInFlight,
        runView,
        isCurrentlyScheduledLive,
        fallback,
        hasLiveWarning: Boolean(liveWarningMessage),
        strategyId: strategy.id,
        isDirty: draft.isDirty,
        statusDetail,
    });

    const persistActiveStrategy = async (
        options: { restore?: boolean } = {},
    ): Promise<StrategyRecipeRecord> => {
        const saved = await draft.save(async (recipe) => {
            const res = await saveRecipeFn({
                data: { recipe, restore: options.restore ?? false },
            });
            return assertServerFnResult(res, 'Saving strategy') as StrategyRecipeRecord;
        });
        setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved));
        return saved;
    };

    const handleSaveRecipe = async () => {
        if (isBusy || !draft.isDirty || hasEmptyPrompt) return;
        const wasUnsaved = !strategy.id;
        try {
            const saved = await persistActiveStrategy({ restore: true });
            if (wasUnsaved && saved.id) {
                await navigate({ to: '/recipes/$recipeId', params: { recipeId: saved.id } });
            }
        } catch {
            // Inline error handled by RecipeNameField
        }
    };

    const handleBacktest = async () => {
        if (isBusy || hasEmptyPrompt) return;
        setIsRunningBacktest(true);
        liveControl.setScheduleError(null);
        let queuedBacktestJobId: string | undefined;
        let didNavigate = false;
        try {
            const saved = await persistActiveStrategy();
            const job = assertServerFnResult(
                await enqueueRecipeJobFn({
                    data: { recipeId: saved.id, mode: 'backtest' },
                }),
                'Starting backtest',
            ) as { id: string; status: string; result_json?: BacktestResultData };
            queuedBacktestJobId = job.id;
            track(posthog, 'run_queued', { recipeId: saved.id, jobId: job.id });
            await navigate({ to: '/recipes/backtest/$jobId', params: { jobId: job.id } });
            didNavigate = true;
            return;
        } catch (err) {
            setBacktestError((prev) => {
                const next = buildBacktestError({ err, queuedBacktestJobId });
                if (!next.backtestJobId && prev?.backtestJobId) {
                    return { ...next, backtestJobId: prev.backtestJobId };
                }
                return next;
            });
        } finally {
            setIsRunningBacktest(false);
            if (!didNavigate) await refreshQuota();
        }
    };

    const handleToggleScheduledLive = () => {
        if (isBusy || hasEmptyPrompt) return;
        setBacktestError(null);
        const target: RecipeSummaryItem = currentSavedRecord ?? {
            id: strategy.id ?? '',
            name: strategy.name,
            cadence: strategy.cadence,
            is_live: isCurrentlyScheduledLive === true,
            // Not saved through this path yet, so it carries the column default.
            is_public: true,
            trial_count: 0,
            updated_at: new Date().toISOString(),
        };
        void liveControl.toggle(target, () => persistActiveStrategy());
    };

    const handleStageChange = (updated: StrategyStage) => {
        draft.setStage(updated);
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

    const handlePledgeSubmit = async (email: string, tier: string, feedback: string) => {
        await submitWaitlistPledgeFn({
            data: { email, intendedTier: tier, feedback },
        });
    };

    return (
        <div className="min-h-screen text-voxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                <div className="flex flex-col gap-6 min-w-0">
                    <h1 className="sr-only">Build a trading bot from one sentence</h1>
                    <div
                        data-testid="compiled-bot-hero-card"
                        className="voxel-card mx-auto flex w-full max-w-4xl flex-col gap-4 rounded-none p-6 min-w-0"
                    >
                        {strategy.id ? (
                            <BuilderBotLiveStatus
                                recipeId={strategy.id}
                                isScheduledLive={isCurrentlyScheduledLive}
                                turboExpiresAt={
                                    currentSavedRecord?.turbo_expires_at ??
                                    liveSummary?.turboExpiresAt ??
                                    null
                                }
                                summary={liveSummary}
                            />
                        ) : null}

                        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-3 min-w-0">
                            {onStartOver ? (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    colorScheme="neutral"
                                    disabled={isBusy}
                                    onClick={onStartOver}
                                >
                                    ← Describe a different bot
                                </Button>
                            ) : (
                                <Link
                                    to="/recipes"
                                    className="text-xs font-normal text-voxel-muted hover:text-voxel-ink underline underline-offset-4"
                                >
                                    ← My Bots
                                </Link>
                            )}
                            <span className="text-xs font-normal uppercase tracking-wider text-accent whitespace-nowrap">
                                Compiled Bot Studio
                            </span>
                        </div>

                        <BuilderStatusStrip
                            phase="ready"
                            label={workspaceStatus.label}
                            tone={workspaceStatus.tone}
                            detail={workspaceStatus.detail}
                            action={
                                run ? (
                                    <Link
                                        to="/recipes/backtest/$jobId"
                                        params={{ jobId: run.id }}
                                        className="text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover"
                                    >
                                        Open run →
                                    </Link>
                                ) : undefined
                            }
                        />

                        <LiveWarningBanner
                            show={workspaceStatus.showLiveWarning}
                            message={liveWarningMessage}
                        />

                        <DataCoverageNote />

                        <CompiledBotSummaryCard
                            strategy={strategy}
                            summary={summary}
                            preferLive={workspaceStatus.preferLive}
                            isPublic={currentSavedRecord?.is_public ?? true}
                            isDirty={draft.isDirty}
                            isBusy={isBusy || hasEmptyPrompt}
                            saveState={draft.saveState}
                            saveError={
                                backtestError || liveControl.scheduleError ? null : draft.saveError
                            }
                            isRunningBacktest={isRunningBacktest}
                            isTogglingLive={liveControl.isBusy}
                            isCurrentlyScheduledLive={isCurrentlyScheduledLive === true}
                            backtestButtonLabel={resolveBacktestButtonLabel(
                                isRunningBacktest,
                                quotaStatus,
                            )}
                            onNameChange={draft.setName}
                            onSave={handleSaveRecipe}
                            onBacktest={handleBacktest}
                            onToggleLive={handleToggleScheduledLive}
                        />

                        {liveControl.state.kind === 'confirming' ||
                        liveControl.state.kind === 'switching' ? (
                            <LiveSwitchConfirmation
                                conflictingRecipe={liveControl.state.conflicting}
                                targetRecipeName={strategy.name}
                                isSwitching={liveControl.state.kind === 'switching'}
                                onConfirm={() =>
                                    void liveControl.confirmSwitch(() => persistActiveStrategy())
                                }
                                onCancel={liveControl.cancelSwitch}
                            />
                        ) : null}

                        <StudioAlertSlot
                            backtestError={backtestError}
                            scheduleError={liveControl.scheduleError}
                            onRequestCapacity={() => setShowPledgeModal(true)}
                        />

                        <BuilderStepper activeStep={3} />
                    </div>

                    <CompiledBotBlueprintSection
                        activeTab={activeTab}
                        onSelectTab={setActiveTab}
                        stage={stage}
                        preview={preview}
                        onStageChange={handleStageChange}
                        onPreviewLiveData={handlePreviewLiveData}
                    />

                    <WaitlistPledgeModal
                        isOpen={showPledgeModal}
                        onClose={() => setShowPledgeModal(false)}
                        onSubmit={handlePledgeSubmit}
                    />
                </div>
            </PageLayout>
        </div>
    );
}
