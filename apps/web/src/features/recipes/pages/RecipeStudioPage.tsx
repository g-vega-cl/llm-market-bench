import { PageLayout } from '@llm-market-bench/ui-design-system';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { fetchRecipeQuotaStatusFn, toggleLiveScheduleFn } from '../api/recipes-quota-api';
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
import { RecipeSaveError, useRecipeDraft } from '../utils/use-recipe-draft';
import { useStrategyRemoval } from '../utils/use-strategy-removal';

interface RecipeStudioPageProps {
    initialStrategy?: PushStrategy | null;
    recentBacktests?: RecipeJobRecord[];
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
}

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
    const strategy = draft.strategy;
    const [activeTemplateIdx, setActiveTemplateIdx] = useState<number>(() =>
        initialStrategy ? -1 : 0,
    );

    const [scheduleError, setScheduleError] = useState<string | null>(null);
    const [backtestError, setBacktestError] = useState<BacktestError | null>(null);
    const [preview, setPreview] = useState<PreviewState>({ status: 'template' });
    const [quotaStatus, setQuotaStatus] = useState<RecipeUserQuotaStatus | null>(initialQuota);
    const [userRecipes, setUserRecipes] = useState<RecipeSummaryItem[]>(initialUserRecipes);
    const removal = useStrategyRemoval((item) => {
        setUserRecipes((prev) => prev.filter((r) => r.id !== item.id));
        if (strategy.id === item.id) {
            // The removed row must not stay open in the editor, otherwise the
            // next Backtest or Schedule Live persist would act on a hidden strategy.
            draft.resetTo(STARTER_RECIPES[0]);
            setActiveTemplateIdx(0);
            setBacktestError(null);
            setScheduleError(null);
            setPreview({ status: 'template' });
        }
    });
    const [isTogglingLive, setIsTogglingLive] = useState(false);
    const [isRunningBacktest, setIsRunningBacktest] = useState(false);

    // Live switch confirmation state
    const [conflictingLiveRecipe, setConflictingLiveRecipe] = useState<RecipeSummaryItem | null>(
        null,
    );
    const [isSwitchingLive, setIsSwitchingLive] = useState(false);

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
        draft.resetTo(STARTER_RECIPES[idx]);
        setScheduleError(null);
        setBacktestError(null);
        setPreview({ status: 'template' });
        setConflictingLiveRecipe(null);
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
        const saved = await draft.save(
            (recipe) =>
                saveRecipeFn({
                    data: { recipe, restore: options.restore ?? false },
                }) as Promise<StrategyRecipeRecord>,
        );
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
        if (isRunningBacktest) return;
        setIsRunningBacktest(true);
        setScheduleError(null);
        let queuedBacktestJobId: string | undefined;
        let didNavigate = false;
        try {
            const saved = await persistActiveStrategy();
            const job = (await enqueueRecipeJobFn({
                data: { recipeId: saved.id, mode: 'backtest' },
            })) as { id: string; status: string; result_json?: BacktestResultData };
            queuedBacktestJobId = job.id;
            await navigate({ to: '/recipes/backtest/$jobId', params: { jobId: job.id } });
            didNavigate = true;
            return;
        } catch (err) {
            // A failed save is reported inline next to the name field; surfacing
            // it here too would duplicate the alert.
            if (!(err instanceof RecipeSaveError)) {
                setBacktestError((prev) => {
                    const next = buildBacktestError({ err, queuedBacktestJobId });
                    // Preserve the queued job id across retries so the fallback
                    // "Open Backtest Run" link stays visible on quota failures.
                    if (!next.backtestJobId && prev?.backtestJobId) {
                        return { ...next, backtestJobId: prev.backtestJobId };
                    }
                    return next;
                });
            }
        } finally {
            setIsRunningBacktest(false);
            if (!didNavigate) await refreshQuota();
        }
    };

    const currentSavedRecord = userRecipes.find((r) => r.id === strategy.id);
    const isCurrentlyScheduledLive = Boolean(currentSavedRecord?.is_live);

    const applyScheduleError = (err: unknown) => {
        // A failed save is reported inline next to the name field.
        if (err instanceof RecipeSaveError) return;
        const message =
            err instanceof Error ? err.message : 'Failed updating Scheduled Live status';
        if (isQuotaLimitMessage(message)) {
            console.warn('[RecipeStudio] Scheduled Live blocked by quota:', message);
        } else {
            console.error('[RecipeStudio] Failed updating Scheduled Live status:', err);
        }
        setScheduleError(message);
    };

    /**
     * Toggle live schedule for the current recipe.
     *
     * When enabling and another recipe is already live, shows a confirmation
     * trough (LiveSwitchConfirmation) instead of silently switching. On confirm,
     * disables the old recipe first, then enables the new one.
     */
    const handleToggleScheduledLive = async () => {
        if (isTogglingLive) return;
        setIsTogglingLive(true);
        setScheduleError(null);
        setBacktestError(null);

        // If currently live, just disable.
        if (isCurrentlyScheduledLive) {
            try {
                const saved = await persistActiveStrategy();
                const updated = await toggleLiveScheduleFn({
                    data: { recipeId: saved.id, isLive: false },
                });
                setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved, updated.is_live));
            } catch (err) {
                applyScheduleError(err);
            } finally {
                setIsTogglingLive(false);
                await refreshQuota();
            }
            return;
        }

        // Check for conflicting live recipe.
        const conflicting = userRecipes.find((r) => r.is_live && r.id !== strategy.id);
        if (conflicting) {
            setIsTogglingLive(false);
            setConflictingLiveRecipe(conflicting);
            return;
        }

        // No conflict — enable directly.
        try {
            const saved = await persistActiveStrategy();
            const updated = await toggleLiveScheduleFn({
                data: { recipeId: saved.id, isLive: true },
            });
            setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved, updated.is_live));
            // Navigate to the live status page.
            await navigate({ to: '/recipes/live/$recipeId', params: { recipeId: saved.id } });
        } catch (err) {
            applyScheduleError(err);
        } finally {
            setIsTogglingLive(false);
            await refreshQuota();
        }
    };

    /**
     * Confirm the live switch: disable the old live recipe, then enable the new one.
     */
    const handleConfirmLiveSwitch = async () => {
        if (!conflictingLiveRecipe || isSwitchingLive) return;
        setIsSwitchingLive(true);
        setScheduleError(null);
        try {
            const saved = await persistActiveStrategy();

            // Disable the old live recipe first.
            await toggleLiveScheduleFn({
                data: { recipeId: conflictingLiveRecipe.id, isLive: false },
            });

            // Enable the new one.
            const updated = await toggleLiveScheduleFn({
                data: { recipeId: saved.id, isLive: true },
            });

            setUserRecipes((prev) => {
                const withoutOld = prev.map((r) =>
                    r.id === conflictingLiveRecipe.id ? { ...r, is_live: false } : r,
                );
                return upsertSavedRecipeSummary(withoutOld, saved, updated.is_live);
            });

            setConflictingLiveRecipe(null);
            await navigate({ to: '/recipes/live/$recipeId', params: { recipeId: saved.id } });
        } catch (err) {
            applyScheduleError(err);
            setConflictingLiveRecipe(null);
        } finally {
            setIsSwitchingLive(false);
            await refreshQuota();
        }
    };

    const handleCancelLiveSwitch = () => {
        setConflictingLiveRecipe(null);
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
                        saveError={draft.saveError}
                        disabled={draft.isSaving || isRunningBacktest}
                    />

                    <StudioActionBar
                        isTogglingLive={isTogglingLive}
                        isCurrentlyScheduledLive={isCurrentlyScheduledLive}
                        liveRecipeId={isCurrentlyScheduledLive ? strategy.id : undefined}
                        isRunningBacktest={isRunningBacktest}
                        backtestButtonLabel={backtestButtonLabel}
                        unreadAlerts={alerts.filter((a) => !a.is_read).length}
                        onOpenWaitlist={() => setShowPledgeModal(true)}
                        onOpenAlerts={handleLoadAlerts}
                        onToggleScheduledLive={handleToggleScheduledLive}
                        onBacktest={handleBacktest}
                    />
                </div>

                {conflictingLiveRecipe && (
                    <LiveSwitchConfirmation
                        conflictingRecipe={conflictingLiveRecipe}
                        targetRecipeName={strategy.name}
                        isSwitching={isSwitchingLive}
                        onConfirm={handleConfirmLiveSwitch}
                        onCancel={handleCancelLiveSwitch}
                    />
                )}

                <StudioAlertSlot
                    backtestError={backtestError}
                    scheduleError={scheduleError}
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
