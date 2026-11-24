import { useState } from 'react';
import { assertServerFnResult } from '~/lib/server-fn';
import { switchLiveScheduleFn, toggleLiveScheduleFn } from '../api/recipes-quota-api';
import type { RecipeSummaryItem, RecipeUserQuotaStatus, StrategyRecipeRecord } from '../types';
import { isQuotaLimitMessage, upsertSavedRecipeSummary } from './live-studio-helpers';

export type LiveScheduleState =
    | { kind: 'idle' }
    | { kind: 'toggling'; recipeId: string }
    | { kind: 'confirming'; target: RecipeSummaryItem; conflicting: RecipeSummaryItem }
    | {
          kind: 'switching';
          target: RecipeSummaryItem;
          conflicting: RecipeSummaryItem;
      };

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
        const message =
            err instanceof Error ? err.message : 'Failed updating Scheduled Live status';
        if (isQuotaLimitMessage(message)) {
            console.warn('[LiveScheduleControl] Scheduled Live blocked by quota:', message);
        } else {
            console.error('[LiveScheduleControl] Failed updating Scheduled Live status:', err);
        }
        setScheduleError(message);
    };

    const enableResolvedLive = async (
        recipeId: string,
        saved: StrategyRecipeRecord | null,
        isLive: boolean,
    ) => {
        const updated = assertServerFnResult(
            await toggleLiveScheduleFn({ data: { recipeId, isLive } }),
            'Updating live schedule',
        );
        onRecipesChange((prev) => {
            if (saved) return upsertSavedRecipeSummary(prev, saved, updated.is_live);
            return prev.map((r) =>
                r.id === recipeId
                    ? {
                          ...r,
                          is_live: updated.is_live,
                          turbo_expires_at: updated.is_live ? r.turbo_expires_at : null,
                      }
                    : r,
            );
        });
    };

    const persistTargetId = async (
        target: RecipeSummaryItem,
        nextLive: boolean,
        persistFirst?: () => Promise<StrategyRecipeRecord>,
    ) => {
        const saved = persistFirst ? await persistFirst() : null;
        const recipeId = saved?.id ?? target.id;
        if (!recipeId) {
            throw new Error(
                nextLive
                    ? 'Could not determine strategy ID to enable live schedule.'
                    : 'Could not determine strategy ID to pause live schedule.',
            );
        }
        return { saved, recipeId };
    };

    const toggle = async (
        target: RecipeSummaryItem,
        persistFirst?: () => Promise<StrategyRecipeRecord>,
    ) => {
        if (isBusy) return;
        setScheduleError(null);

        const conflicting = !target.is_live
            ? userRecipes.filter((r) => r.is_live && r.id !== target.id)
            : [];
        if (conflicting.length >= maxLiveRecipes) {
            setState({ kind: 'confirming', target, conflicting: conflicting[0] });
            return;
        }

        const nextLive = !target.is_live;
        setState({ kind: 'toggling', recipeId: target.id });
        let didNavigate = false;
        try {
            const { saved, recipeId } = await persistTargetId(target, nextLive, persistFirst);
            await enableResolvedLive(recipeId, saved, nextLive);
            if (nextLive && onEnabledNavigate) {
                await onEnabledNavigate(recipeId);
                didNavigate = true;
            }
        } catch (err) {
            applyScheduleError(err);
        } finally {
            setState({ kind: 'idle' });
            if (!didNavigate) await onRefreshQuota();
        }
    };

    const confirmSwitch = async (persistFirst?: () => Promise<StrategyRecipeRecord>) => {
        if (state.kind !== 'confirming') return;
        const { target, conflicting } = state;
        setState({ kind: 'switching', target, conflicting });
        setScheduleError(null);
        let didNavigate = false;
        try {
            const { saved, recipeId } = await persistTargetId(target, true, persistFirst);
            const switched = assertServerFnResult(
                await switchLiveScheduleFn({
                    data: { pauseRecipeId: conflicting.id, enableRecipeId: recipeId },
                }),
                'Switching live schedule',
            );

            onRecipesChange((prev) => {
                const withoutOld = prev.map((r) =>
                    r.id === conflicting.id ? { ...r, is_live: false, turbo_expires_at: null } : r,
                );
                if (saved) return upsertSavedRecipeSummary(withoutOld, saved, switched.is_live);
                return withoutOld.map((r) =>
                    r.id === recipeId ? { ...r, is_live: switched.is_live } : r,
                );
            });

            setState({ kind: 'idle' });
            if (onEnabledNavigate) {
                await onEnabledNavigate(recipeId);
                didNavigate = true;
            }
        } catch (err) {
            applyScheduleError(err);
            setState({ kind: 'idle' });
        } finally {
            if (!didNavigate) await onRefreshQuota();
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
