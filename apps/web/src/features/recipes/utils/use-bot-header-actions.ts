import { usePostHog } from '@posthog/react';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { track } from '~/lib/analytics';
import { assertServerFnResult } from '~/lib/server-fn';
import { forkRecipeFn } from '../api/fork-recipe';
import { enqueueRecipeJobFn } from '../api/recipes-api';
import { fetchRecipeQuotaStatusFn } from '../api/recipes-quota-api';
import { submitWaitlistPledgeFn } from '../api/recipes-studio-api';
import type {
    BacktestError,
    BacktestResultData,
    RecipeCadence,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
    StrategyRecipeRecord,
} from '../types';
import { buildBacktestError } from './live-studio-helpers';
import { useLiveScheduleControl } from './use-live-schedule-control';

export interface UseBotHeaderActionsArgs {
    recipeId: string;
    recipeName: string;
    cadence: RecipeCadence;
    initialIsLive: boolean;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
    externalBusy?: boolean;
    persistBeforeAction?: () => Promise<StrategyRecipeRecord>;
    onNavigateAfterEnableLive?: boolean;
}

/**
 * Shared action state (run backtest, toggle/switch live schedule, fork public bot,
 * waitlist capacity modal) for `BotStageHeader` across Overview, Live Runs, and Blueprint.
 */
export function useBotHeaderActions({
    recipeId,
    recipeName,
    cadence,
    initialIsLive,
    initialQuota = null,
    initialUserRecipes = [],
    externalBusy = false,
    persistBeforeAction,
    onNavigateAfterEnableLive = false,
}: UseBotHeaderActionsArgs) {
    const navigate = useNavigate();
    const posthog = usePostHog();

    const [quotaStatus, setQuotaStatus] = useState<RecipeUserQuotaStatus | null>(initialQuota);
    const [userRecipes, setUserRecipes] = useState<RecipeSummaryItem[]>(initialUserRecipes);
    const [isRunningBacktest, setIsRunningBacktest] = useState(false);
    const [backtestError, setBacktestError] = useState<BacktestError | null>(null);
    const [isForking, setIsForking] = useState(false);
    const [forkError, setForkError] = useState<string | null>(null);
    const [showPledgeModal, setShowPledgeModal] = useState(false);

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
        onEnabledNavigate: onNavigateAfterEnableLive
            ? async (enabledId) => {
                  await navigate({
                      to: '/recipes/live/$recipeId',
                      params: { recipeId: enabledId },
                  });
              }
            : undefined,
    });

    const currentSavedRecord = userRecipes.find((r) => r.id === recipeId);
    const isLive = currentSavedRecord ? currentSavedRecord.is_live : initialIsLive;

    const handleBacktest = async () => {
        if (externalBusy || isRunningBacktest || liveControl.isBusy) return;
        setIsRunningBacktest(true);
        setBacktestError(null);
        liveControl.setScheduleError(null);
        let queuedBacktestJobId: string | undefined;
        let didNavigate = false;
        try {
            const saved = persistBeforeAction ? await persistBeforeAction() : null;
            const targetId = saved?.id ?? recipeId;
            const job = assertServerFnResult(
                await enqueueRecipeJobFn({
                    data: { recipeId: targetId, mode: 'backtest' },
                }),
                'Starting backtest',
            ) as { id: string; status: string; result_json?: BacktestResultData };
            queuedBacktestJobId = job.id;
            track(posthog, 'run_queued', { recipeId: targetId, jobId: job.id });
            await navigate({ to: '/recipes/backtest/$jobId', params: { jobId: job.id } });
            didNavigate = true;
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

    const handleToggleLive = () => {
        if (externalBusy || isRunningBacktest || liveControl.isBusy) return;
        setBacktestError(null);
        const target: RecipeSummaryItem = currentSavedRecord ?? {
            id: recipeId,
            name: recipeName,
            cadence,
            is_live: isLive,
            trial_count: 0,
            updated_at: new Date().toISOString(),
        };
        void liveControl.toggle(target, persistBeforeAction);
    };

    const handleConfirmSwitch = () => {
        void liveControl.confirmSwitch(persistBeforeAction);
    };

    const handleFork = async () => {
        if (isForking) return;
        setIsForking(true);
        setForkError(null);
        try {
            const created = assertServerFnResult(
                await forkRecipeFn({ data: { recipeId } }),
                'Forking recipe',
            );
            track(posthog, 'recipe_forked', { recipeId });
            await navigate({ to: '/recipes/$recipeId', params: { recipeId: created.id } });
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Failed to fork bot';
            if (/unauthorized|sign in/i.test(msg)) {
                await navigate({
                    to: '/auth',
                    search: { redirect: `/recipes/${recipeId}` },
                });
                return;
            }
            setForkError(msg);
        } finally {
            setIsForking(false);
        }
    };

    const handlePledgeSubmit = async (email: string, tier: string, feedback: string) => {
        await submitWaitlistPledgeFn({
            data: { email, intendedTier: tier, feedback },
        });
    };

    return {
        quotaStatus,
        userRecipes,
        setUserRecipes,
        isLive,
        isRunningBacktest,
        backtestError,
        isForking,
        forkError,
        showPledgeModal,
        setShowPledgeModal,
        liveControl,
        handleBacktest,
        handleToggleLive,
        handleConfirmSwitch,
        handleFork,
        handlePledgeSubmit,
    };
}
