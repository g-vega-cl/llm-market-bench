import { useState } from 'react';
import { toggleLiveScheduleFn } from '../api/recipes-quota-api';
import type { RecipeSummaryItem, RecipeUserQuotaStatus, StrategyRecipeRecord } from '../types';
import { isQuotaLimitMessage, upsertSavedRecipeSummary } from './live-studio-helpers';
import { RecipeSaveError } from './use-recipe-draft';

export type LiveScheduleState =
    | { kind: 'idle' }
    | { kind: 'toggling'; recipeId: string }
    | { kind: 'confirming'; target: RecipeSummaryItem; conflicting: RecipeSummaryItem }
    | { kind: 'switching'; targetId: string };

export interface UseLiveScheduleControlArgs {
    userRecipes: RecipeSummaryItem[];
    quotaStatus: RecipeUserQuotaStatus | null;
    onRecipesChange: React.Dispatch<React.SetStateAction<RecipeSummaryItem[]>>;
    onRefreshQuota: () => Promise<void>;
    onEnabledNavigate?: (recipeId: string) => Promise<void>;
}

/**
 * Shared state machine for toggling a recipe's Live (30m) schedule,
 * handling maxLiveRecipes conflict confirmation and partial-failure sync.
 */
export function useLiveScheduleControl({
    userRecipes,
    quotaStatus,
    onRecipesChange,
    onRefreshQuota,
    onEnabledNavigate,
}: UseLiveScheduleControlArgs) {
    const [state, setState] = useState<LiveScheduleState>({ kind: 'idle' });
    const [scheduleError, setScheduleError] = useState<string | null>(null);

    const isBusy = state.kind === 'toggling' || state.kind === 'switching';
    const maxLiveRecipes = quotaStatus?.maxLiveRecipes ?? 3;

    const applyScheduleError = (err: unknown) => {
        if (err instanceof RecipeSaveError) return;
        const message =
            err instanceof Error ? err.message : 'Failed updating Scheduled Live status';
        if (!isQuotaLimitMessage(message)) {
            console.error('[LiveScheduleControl] Failed updating Scheduled Live status:', err);
        }
        setScheduleError(message);
    };

    const toggle = async (
        target: RecipeSummaryItem,
        persistFirst?: () => Promise<StrategyRecipeRecord>,
    ) => {
        if (isBusy) return;
        setScheduleError(null);

        if (target.is_live) {
            setState({ kind: 'toggling', recipeId: target.id });
            try {
                const saved = persistFirst ? await persistFirst() : null;
                const recipeId = saved?.id ?? target.id;
                const updated = await toggleLiveScheduleFn({ data: { recipeId, isLive: false } });
                onRecipesChange((prev) =>
                    saved
                        ? upsertSavedRecipeSummary(prev, saved, updated.is_live)
                        : prev.map((r) =>
                              r.id === recipeId
                                  ? { ...r, is_live: updated.is_live, turbo_expires_at: null }
                                  : r,
                          ),
                );
            } catch (err) {
                applyScheduleError(err);
            } finally {
                setState({ kind: 'idle' });
                await onRefreshQuota();
            }
            return;
        }

        const activeOtherLive = userRecipes.filter((r) => r.is_live && r.id !== target.id);
        if (activeOtherLive.length >= maxLiveRecipes) {
            setState({ kind: 'confirming', target, conflicting: activeOtherLive[0] });
            return;
        }

        setState({ kind: 'toggling', recipeId: target.id });
        try {
            const saved = persistFirst ? await persistFirst() : null;
            const recipeId = saved?.id ?? target.id;
            const updated = await toggleLiveScheduleFn({ data: { recipeId, isLive: true } });
            onRecipesChange((prev) =>
                saved
                    ? upsertSavedRecipeSummary(prev, saved, updated.is_live)
                    : prev.map((r) => (r.id === recipeId ? { ...r, is_live: updated.is_live } : r)),
            );
            if (onEnabledNavigate) {
                await onEnabledNavigate(recipeId);
            }
        } catch (err) {
            applyScheduleError(err);
        } finally {
            setState({ kind: 'idle' });
            await onRefreshQuota();
        }
    };

    const confirmSwitch = async (persistFirst?: () => Promise<StrategyRecipeRecord>) => {
        if (state.kind !== 'confirming') return;
        const { target, conflicting } = state;
        setState({ kind: 'switching', targetId: target.id });
        setScheduleError(null);
        try {
            await toggleLiveScheduleFn({ data: { recipeId: conflicting.id, isLive: false } });
            // Sync disabled state immediately so a failure on the second call never leaves UI stale.
            onRecipesChange((prev) =>
                prev.map((r) =>
                    r.id === conflicting.id ? { ...r, is_live: false, turbo_expires_at: null } : r,
                ),
            );

            const saved = persistFirst ? await persistFirst() : null;
            const recipeId = saved?.id ?? target.id;
            const updated = await toggleLiveScheduleFn({ data: { recipeId, isLive: true } });
            onRecipesChange((prev) =>
                saved
                    ? upsertSavedRecipeSummary(prev, saved, updated.is_live)
                    : prev.map((r) => (r.id === recipeId ? { ...r, is_live: updated.is_live } : r)),
            );
            setState({ kind: 'idle' });
            if (onEnabledNavigate) {
                await onEnabledNavigate(recipeId);
            }
        } catch (err) {
            applyScheduleError(err);
            setState({ kind: 'idle' });
        } finally {
            await onRefreshQuota();
        }
    };

    const cancelSwitch = () => {
        if (state.kind === 'confirming') {
            setState({ kind: 'idle' });
        }
    };

    return {
        state,
        isBusy,
        scheduleError,
        setScheduleError,
        toggle,
        confirmSwitch,
        cancelSwitch,
    };
}
