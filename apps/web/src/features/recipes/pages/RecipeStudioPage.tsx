import { PageLayout } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useNavigate } from '@tanstack/react-router';
import { useEffect, useRef, useState } from 'react';
import {
    ARCHETYPES,
    CODE_BY_RECIPE_NAME,
    TYPE_GRID,
} from '~/features/personality/personality-data';
import { track } from '~/lib/analytics';
import { assertServerFnResult } from '~/lib/server-fn';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { activateRecipeTurboFn, fetchRecipeQuotaStatusFn } from '../api/recipes-quota-api';
import {
    fetchRecipeAlertsFn,
    markAlertReadFn,
    previewStrategyPromptFn,
    submitWaitlistPledgeFn,
} from '../api/recipes-studio-api';
import { LiveSwitchConfirmation } from '../components/LiveSwitchConfirmation';
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
import { StudioActionBar } from '../components/StudioActionBar';
import { StudioHeader } from '../components/StudioHeader';
import { TemplatePickerBar } from '../components/TemplatePickerBar';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import { STARTER_RECIPES } from '../starter-templates';
import type {
    BacktestError,
    BacktestResultData,
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
    buildBacktestError,
    isQuotaLimitMessage,
    upsertSavedRecipeSummary,
} from '../utils/live-studio-helpers';
import { clearLocalDraft, loadLocalDraft } from '../utils/local-draft';
import { useLiveScheduleControl } from '../utils/use-live-schedule-control';
import { useRecipeDraft } from '../utils/use-recipe-draft';
import { useStrategyRemoval } from '../utils/use-strategy-removal';

interface RecipeStudioPageProps {
    initialStrategy?: PushStrategy | null;
    recentBacktests?: RecipeJobRecord[];
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
}

const TEMPLATE_GRID_ROWS = ['LV', 'LN', 'QV', 'QN'];
const TEMPLATE_GRID_COLUMNS = ['FP', 'FR', 'MP', 'MR'];

/** The 16 starter templates as the shared 4x4 type-code grid, in row-major order. */
const TEMPLATE_GRID_CELLS = TYPE_GRID.map((cell) => ({
    code: cell.code,
    label: cell.archetypeId ? ARCHETYPES[cell.archetypeId].title : cell.code,
}));

export function RecipeStudioPage({
    initialStrategy = null,
    recentBacktests = [],
    initialQuota = null,
    initialUserRecipes = [],
}: RecipeStudioPageProps = {}) {
    const navigate = useNavigate();
    const draft = useRecipeDraft(
        initialStrategy ?? STARTER_RECIPES[0],
        initialStrategy?.name ?? null,
    );
    // A recipe compiled in /build (or typed while logged out) is parked in this
    // browser. It is adopted in an effect, not a state initializer: reading
    // localStorage during render makes the first client paint differ from SSR.
    const importedRef = useRef(false);
    useEffect(() => {
        if (initialStrategy || importedRef.current) return;
        importedRef.current = true;
        const local = loadLocalDraft();
        if (!local) return;
        draft.resetTo(local.strategy);
        clearLocalDraft();
    }, [initialStrategy, draft]);
    const strategy = draft.strategy;
    const posthog = usePostHog();
    const [activeTemplateIdx, setActiveTemplateIdx] = useState<number>(() =>
        initialStrategy ? -1 : 0,
    );

    const [backtestError, setBacktestError] = useState<BacktestError | null>(null);
    const [preview, setPreview] = useState<PreviewState>({ status: 'template' });
    const [quotaStatus, setQuotaStatus] = useState<RecipeUserQuotaStatus | null>(initialQuota);
    const [userRecipes, setUserRecipes] = useState<RecipeSummaryItem[]>(initialUserRecipes);
    const [isActivatingTurbo, setIsActivatingTurbo] = useState(false);
    const [isRunningBacktest, setIsRunningBacktest] = useState(false);
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

    const liveControl = useLiveScheduleControl({
        userRecipes,
        quotaStatus,
        onRecipesChange: setUserRecipes,
        onRefreshQuota: refreshQuota,
        onEnabledNavigate: async (recipeId) => {
            await navigate({ to: '/recipes/live/$recipeId/runs', params: { recipeId } });
        },
    });

    const removal = useStrategyRemoval((item) => {
        setUserRecipes((prev) => prev.filter((r) => r.id !== item.id));
        if (strategy.id === item.id) {
            // The removed row must not stay open in the editor, otherwise the
            // next Backtest or Schedule Live persist would act on a hidden strategy.
            draft.resetTo(STARTER_RECIPES[0]);
            setActiveTemplateIdx(0);
            setBacktestError(null);
            liveControl.setScheduleError(null);
            setPreview({ status: 'template' });
        }
    });

    const handleSelectTemplate = (idx: number) => {
        setActiveTemplateIdx(idx);
        draft.resetTo(STARTER_RECIPES[idx]);
        liveControl.setScheduleError(null);
        liveControl.cancelSwitch();
        setBacktestError(null);
        setPreview({ status: 'template' });
    };

    const handleSelectTemplateByCode = (code: string) => {
        const archetypeId = TYPE_GRID.find((cell) => cell.code === code)?.archetypeId;
        if (!archetypeId) return;
        const index = STARTER_RECIPES.findIndex(
            (recipe) => recipe.name === ARCHETYPES[archetypeId].recipeName,
        );
        if (index >= 0) handleSelectTemplate(index);
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

    const persistActiveStrategy = async (
        options: { restore?: boolean } = {},
    ): Promise<StrategyRecipeRecord> => {
        // One in-flight save at a time: run/schedule callers share the promise,
        // so a recipe can never be inserted twice from a duplicate click.
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
        if (draft.isSaving || !draft.isDirty) return;
        try {
            // The header button is the only explicit restore: it is what brings a
            // strategy removed from My Strategies back into the list.
            await persistActiveStrategy({ restore: true });
        } catch {
            // Draft state surfaces the message inline next to the field.
        }
    };

    const handleBacktest = async () => {
        if (isRunningBacktest || liveControl.isBusy || draft.isSaving) return;
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
            // The activation funnel ends here in the client: the runner settles the
            // job server-side, where no PostHog client exists.
            track(posthog, 'run_queued', { recipeId: saved.id, jobId: job.id });
            await navigate({ to: '/recipes/backtest/$jobId', params: { jobId: job.id } });
            didNavigate = true;
            return;
        } catch (err) {
            setBacktestError((prev) => {
                const next = buildBacktestError({ err, queuedBacktestJobId });
                // Preserve the queued job id across retries so the fallback
                // "Open Backtest Run" link stays visible on quota failures.
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

    const currentSavedRecord = userRecipes.find((r) => r.id === strategy.id);
    const isCurrentlyScheduledLive = Boolean(currentSavedRecord?.is_live);

    const handleToggleScheduledLive = () => {
        if (liveControl.isBusy) return;
        setBacktestError(null);
        const target: RecipeSummaryItem = currentSavedRecord ?? {
            id: strategy.id ?? '',
            name: strategy.name,
            cadence: strategy.cadence,
            is_live: isCurrentlyScheduledLive,
            // Not yet saved through this path, so it carries the column default.
            is_public: true,
            trial_count: 0,
            updated_at: new Date().toISOString(),
        };
        void liveControl.toggle(target, () => persistActiveStrategy());
    };

    const handleActivateTurbo = async () => {
        if (isActivatingTurbo || !strategy.id || !isCurrentlyScheduledLive) return;
        setIsActivatingTurbo(true);
        liveControl.setScheduleError(null);
        setBacktestError(null);
        try {
            const res = assertServerFnResult(
                await activateRecipeTurboFn({ data: { recipeId: strategy.id } }),
                'Activating Turbo',
            );
            setUserRecipes((prev) =>
                prev.map((r) =>
                    r.id === res.recipeId ? { ...r, turbo_expires_at: res.turboExpiresAt } : r,
                ),
            );
            setQuotaStatus((prev) => (prev ? { ...prev, turboUsedToday: true } : prev));
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed activating Turbo';
            if (isQuotaLimitMessage(message)) {
                console.warn('[RecipeStudio] Turbo blocked by quota:', message);
            } else {
                console.error('[RecipeStudio] Failed activating Turbo:', err);
            }
            liveControl.setScheduleError(message);
        } finally {
            setIsActivatingTurbo(false);
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

    const backtestButtonLabel = resolveBacktestButtonLabel(isRunningBacktest, quotaStatus);

    return (
        <PageLayout>
            <div className="flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-4">
                    <StudioHeader
                        name={strategy.name}
                        onNameChange={draft.setName}
                        onSave={handleSaveRecipe}
                        isDirty={draft.isDirty}
                        saveState={draft.saveState}
                        saveError={
                            backtestError || liveControl.scheduleError ? null : draft.saveError
                        }
                        disabled={draft.isSaving || isRunningBacktest}
                    />

                    <StudioActionBar
                        isTogglingLive={liveControl.isBusy}
                        isCurrentlyScheduledLive={isCurrentlyScheduledLive}
                        liveRecipeId={isCurrentlyScheduledLive ? strategy.id : undefined}
                        turboExpiresAt={currentSavedRecord?.turbo_expires_at}
                        turboUsedToday={quotaStatus?.turboUsedToday}
                        isActivatingTurbo={isActivatingTurbo}
                        isRunningBacktest={isRunningBacktest}
                        backtestButtonLabel={backtestButtonLabel}
                        unreadAlerts={alerts.filter((a) => !a.is_read).length}
                        onOpenWaitlist={() => setShowPledgeModal(true)}
                        onOpenAlerts={handleLoadAlerts}
                        onToggleScheduledLive={handleToggleScheduledLive}
                        onActivateTurbo={
                            isCurrentlyScheduledLive && strategy.id
                                ? handleActivateTurbo
                                : undefined
                        }
                        onBacktest={handleBacktest}
                    />
                </div>

                {(liveControl.state.kind === 'confirming' ||
                    liveControl.state.kind === 'switching') && (
                    <LiveSwitchConfirmation
                        conflictingRecipe={liveControl.state.conflicting}
                        targetRecipeName={strategy.name}
                        isSwitching={liveControl.state.kind === 'switching'}
                        onConfirm={() =>
                            void liveControl.confirmSwitch(() => persistActiveStrategy())
                        }
                        onCancel={liveControl.cancelSwitch}
                    />
                )}

                <StudioAlertSlot
                    backtestError={backtestError}
                    scheduleError={liveControl.scheduleError}
                    onRequestCapacity={() => setShowPledgeModal(true)}
                />

                <RecipeGuideAndQuotaBlock quotaStatus={quotaStatus} />

                <SavedRecipesStrip
                    recipes={userRecipes}
                    activeRecipeId={strategy.id}
                    onRemove={removal.remove}
                    removingId={removal.removingId}
                    errorMessage={removal.errorMessage}
                />

                <RecentBacktestsStrip recentBacktests={recentBacktests} />

                <TemplatePickerBar
                    templates={STARTER_RECIPES}
                    activeIndex={activeTemplateIdx}
                    disabled={draft.isSaving || isRunningBacktest}
                    onSelect={handleSelectTemplate}
                    grid={{
                        cells: TEMPLATE_GRID_CELLS,
                        rowHeaders: TEMPLATE_GRID_ROWS,
                        columnHeaders: TEMPLATE_GRID_COLUMNS,
                        activeCode:
                            activeTemplateIdx >= 0
                                ? CODE_BY_RECIPE_NAME.get(
                                      STARTER_RECIPES[activeTemplateIdx]?.name ?? '',
                                  )
                                : undefined,
                        onSelectCode: handleSelectTemplateByCode,
                        description:
                            activeTemplateIdx >= 0
                                ? `${String(STARTER_RECIPES[activeTemplateIdx]?.name ?? '')} - ${String(
                                      STARTER_RECIPES[activeTemplateIdx]?.description ?? '',
                                  )}`
                                : undefined,
                    }}
                />

                <div className="flex flex-col gap-4">
                    <StageBuilder stage={strategy.stages[0]} onChange={handleStageChange} />
                    <PromptVisualizer
                        stage={strategy.stages[0]}
                        previewState={preview}
                        onPreviewLiveData={handlePreviewLiveData}
                    />
                </div>

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
