import { getNextLiveSlotLabel } from '~/features/recipes/utils/market-hours';

export type LaunchBlockedReason = 'daily-cap' | 'concurrent-cap' | 'queue-full' | 'live-cap';

export type LaunchResult =
    | {
          kind: 'backtest';
          recipeId: string;
          jobId: string;
          live: 'live' | 'denied' | 'not-requested';
          nextSlotLabel: string;
          queuePosition: number | null;
      }
    | { kind: 'live-only'; recipeId: string; nextSlotLabel: string }
    | {
          kind: 'blocked';
          /** Null when nothing was kept: a refused launch leaves no recipe behind. */
          recipeId: string | null;
          reason: LaunchBlockedReason;
          nextResetLabel: string;
      }
    | { kind: 'invalid'; message: string }
    | { kind: 'error'; retryable: boolean; message: string; needsAuth?: boolean };

const BLOCK_REASONS = new Set<string>(['daily-cap', 'concurrent-cap', 'queue-full', 'live-cap']);

function asString(value: unknown): string | null {
    return typeof value === 'string' && value.length > 0 ? value : null;
}

function asNumber(value: unknown): number | null {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

/**
 * The RPC returns nullable columns (RETURNS TABLE makes every column nullable),
 * and the admin client is untyped, so the row is checked before it is trusted —
 * never cast into the union.
 */
export function normalizeLaunchRow(row: unknown, now: Date = new Date()): LaunchResult {
    if (!row || typeof row !== 'object') {
        return { kind: 'error', retryable: true, message: 'The run request returned nothing.' };
    }
    const record = row as Record<string, unknown>;
    const recipeId = asString(record.recipe_id);
    const reason = asString(record.reason);
    const liveState = asString(record.live_state);
    const jobId = asString(record.job_id);

    // A cap is classified before the id check: a refused launch has no recipe.
    if (reason && BLOCK_REASONS.has(reason)) {
        return {
            kind: 'blocked',
            recipeId,
            reason: reason as LaunchBlockedReason,
            nextResetLabel: nextResetLabel(reason as LaunchBlockedReason),
        };
    }

    if (!recipeId) {
        if (reason === 'invalid-graph') {
            return {
                kind: 'invalid',
                message: 'That graph cannot run: it needs one answer block.',
            };
        }
        return { kind: 'error', retryable: true, message: 'The run request lost its recipe.' };
    }

    const nextSlotLabel = getNextLiveSlotLabel(now);
    if (jobId) {
        return {
            kind: 'backtest',
            recipeId,
            jobId,
            live:
                liveState === 'live' ? 'live' : liveState === 'denied' ? 'denied' : 'not-requested',
            nextSlotLabel,
            queuePosition: asNumber(record.queue_position),
        };
    }
    return { kind: 'live-only', recipeId, nextSlotLabel };
}

export function nextResetLabel(reason: LaunchBlockedReason): string {
    if (reason === 'concurrent-cap') return 'as soon as your running backtest finishes';
    if (reason === 'queue-full') return 'in a few minutes, when the shared queue drains';
    if (reason === 'live-cap') return 'when you remove one of your live bots';
    return 'tomorrow (limits reset daily)';
}

/** Human copy for each outcome. Kept beside the union so no surface invents its own. */
export function launchMessage(result: LaunchResult): string {
    if (result.kind === 'backtest') {
        const live =
            result.live === 'live'
                ? ` It goes live at the next slot: ${result.nextSlotLabel}.`
                : result.live === 'denied'
                  ? ' It is saved but not live — you are at your live-bot limit.'
                  : '';
        const queue =
            result.queuePosition === null
                ? ''
                : ` Queue position ${Math.max(1, result.queuePosition + 1)}.`;
        return `Backtest queued.${live}${queue}`;
    }
    if (result.kind === 'live-only') {
        return `Saved and live. First decision ${result.nextSlotLabel}.`;
    }
    if (result.kind === 'blocked') {
        return `Saved, but no run was queued — ${result.nextResetLabel}.`;
    }
    if (result.kind === 'invalid') return result.message;
    return result.message;
}
