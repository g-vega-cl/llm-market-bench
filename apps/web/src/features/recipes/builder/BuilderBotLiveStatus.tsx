import { Badge } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { formatEasternDateTime } from '~/utils/date';
import type { RecipeJobRecord } from '../types';
import {
    formatTurboRemainingLabel,
    getNextLiveSlotLabel,
    LIVE_CADENCE_LABEL,
    TURBO_CADENCE_LABEL,
} from '../utils/market-hours';
import type { RecipeLiveSummary } from './live-summary';

/** ET slots sit on wall-clock :00/:30, so the clock wakes on minute boundaries. */
const MINUTE_MS = 60_000;

const TURN_TONE = {
    success: 'text-success',
    danger: 'text-danger',
    muted: 'text-voxel-muted',
} as const;

interface LiveStateView {
    label: string;
    tone: 'success' | 'accent' | 'neutral';
    /** `null` when the schedule could not be read at all. */
    isLive: boolean | null;
}

export function resolveLiveState(isScheduledLive: boolean | null): LiveStateView {
    if (isScheduledLive === null)
        return { label: 'SCHEDULE UNKNOWN', tone: 'neutral', isLive: null };
    if (!isScheduledLive) return { label: 'PAUSED', tone: 'neutral', isLive: false };
    // The badge stays time-independent so it never disagrees across hydration and
    // never re-announces: the Turbo countdown lives in the next-run line.
    return { label: `LIVE ON (${LIVE_CADENCE_LABEL})`, tone: 'success', isLive: true };
}

export function describeNextRun(
    isLive: boolean | null,
    turboRemaining: string | null,
    now: Date,
): string {
    if (isLive === null) return 'Next run unknown';
    if (!isLive) return 'Next run Paused';
    if (turboRemaining) return `Next run within ${TURBO_CADENCE_LABEL} (Turbo) · ${turboRemaining}`;
    return `Next run ${getNextLiveSlotLabel(now)}`;
}

/** Enough of the provider's message to act on, never a serialized stack. */
const REASON_MAX = 80;

/**
 * `known: false` means no run list was read (a failed read, or a bot that was
 * saved in this session and never loaded) — that is not the same fact as "this
 * bot has never traded", so it must not claim a history either way.
 */
export function describeLastTurn(
    run: RecipeJobRecord | null,
    known = true,
): {
    text: string;
    tone: keyof typeof TURN_TONE;
} {
    if (!known) return { text: 'Live history not loaded', tone: 'muted' };
    if (!run) return { text: 'No live turns yet', tone: 'muted' };
    const stamp = formatEasternDateTime(run.completed_at ?? run.created_at ?? null);
    switch (run.status) {
        case 'completed':
            return { text: `Last turn ${stamp} · completed`, tone: 'success' };
        case 'failed': {
            const reason = run.error_message?.trim();
            const detail = reason
                ? ` — ${reason.length > REASON_MAX ? `${reason.slice(0, REASON_MAX)}…` : reason}`
                : '';
            return { text: `Last turn ${stamp} · failed${detail}`, tone: 'danger' };
        }
        case 'processing':
            return { text: `Last turn ${stamp} · running`, tone: 'muted' };
        case 'pending':
            return { text: `Last turn ${stamp} · queued`, tone: 'muted' };
        case 'cancelled':
            return { text: `Last turn ${stamp} · cancelled`, tone: 'muted' };
        default:
            // A status this build does not know is reported as itself, never as
            // a cancellation it cannot prove.
            return { text: `Last turn ${stamp} · ${run.status}`, tone: 'muted' };
    }
}

function formatUsd(value: number): string {
    return value.toLocaleString('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

/**
 * Cash and equity exactly as the ledger stores them. No return percentage:
 * nothing in `strategy_recipes` records the starting balance, so any delta would
 * be measured against an invented constant instead of the bot's own anchor.
 */
export function describeLedger(
    totalEquity: number | null | undefined,
    cash: number | null | undefined,
): string | null {
    if (typeof totalEquity !== 'number' || !Number.isFinite(totalEquity)) return null;
    const parts = [`Equity ${formatUsd(totalEquity)}`];
    if (typeof cash === 'number' && Number.isFinite(cash)) parts.push(`Cash ${formatUsd(cash)}`);
    return parts.join(' · ');
}

export interface BuilderBotLiveStatusProps {
    recipeId: string;
    /** `null` when the schedule could not be read (no record and no snapshot). */
    isScheduledLive: boolean | null;
    turboExpiresAt?: string | null;
    /** The four live facts this block needs, not the live page's whole payload. */
    summary?: RecipeLiveSummary | null;
}

/**
 * First block of the compiled-bot workspace: is this bot scheduled, when does it
 * run next, how did the last live turn end, and what is the paper ledger worth.
 * The work axis (draft, backtest in flight, prompt needed) stays in
 * BuilderStatusStrip directly below — one status surface cannot cover both.
 *
 * Only the state badge is a polite live region: it changes when the user enables,
 * pauses or turbo-boosts the bot and should be announced once. The next-run label
 * ticks with the clock, so it stays outside the region to avoid one announcement
 * per tick.
 */
export function BuilderBotLiveStatus({
    recipeId,
    isScheduledLive,
    turboExpiresAt = null,
    summary = null,
}: BuilderBotLiveStatusProps) {
    const [now, setNow] = useState(() => new Date());

    useEffect(() => {
        // Re-read the wall clock as soon as the effect runs: the server-rendered
        // label came from the server's minute, and correctness must not wait for
        // the first timer to fire a whole minute later.
        setNow(new Date());
        let timer: ReturnType<typeof setTimeout>;
        const schedule = () => {
            // Wake just past each wall-clock minute so the slot label can never
            // advertise a boundary that has already passed.
            const delay = MINUTE_MS - (Date.now() % MINUTE_MS) + 100;
            timer = setTimeout(() => {
                setNow(new Date());
                schedule();
            }, delay);
        };
        schedule();
        return () => clearTimeout(timer);
    }, []);

    const turboRemaining =
        isScheduledLive === true ? formatTurboRemainingLabel(turboExpiresAt, now) : null;
    const state = resolveLiveState(isScheduledLive);
    // A summary the component has decided is not the viewer's bot must not leak
    // that bot's ledger or run history either; today's call sites cannot pass one,
    // and this keeps the default safe if they ever can.
    const summaryIsOwned = summary?.isOwner !== false;
    const historyKnown = Boolean(summary) && summaryIsOwned;
    const lastTurn = describeLastTurn(summary?.lastRun ?? null, historyKnown);
    const ledger = summaryIsOwned ? describeLedger(summary?.totalEquity, summary?.cash) : null;
    const asOf = summary?.fetchedAt ? `as of ${formatEasternDateTime(summary.fetchedAt)}` : null;

    return (
        <section
            data-testid="bot-live-status"
            aria-label="Live status"
            className="voxel-trough bg-voxel-trough flex flex-col gap-2 p-4 min-w-0"
        >
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 min-w-0">
                <span role="status" aria-live="polite">
                    <Badge
                        variant={state.isLive === true ? 'solid' : 'soft'}
                        size="md"
                        colorScheme={state.tone}
                        showDot
                    >
                        {state.label}
                    </Badge>
                </span>
                <span className="text-sm font-bold text-voxel-ink min-w-0" suppressHydrationWarning>
                    {describeNextRun(state.isLive, turboRemaining, now)}
                </span>
                {state.isLive !== false ? (
                    <Link
                        to="/recipes/live/$recipeId/runs"
                        params={{ recipeId }}
                        className="text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover whitespace-nowrap"
                    >
                        Open live runs →
                    </Link>
                ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 min-w-0">
                <span
                    className={`text-xs font-normal ${TURN_TONE[lastTurn.tone]} min-w-0 break-words`}
                >
                    {lastTurn.text}
                </span>
                {ledger ? (
                    <span className="text-xs font-normal text-voxel-muted whitespace-nowrap">
                        {ledger}
                    </span>
                ) : null}
                {ledger && asOf ? (
                    <span
                        className="text-xs font-normal text-voxel-muted whitespace-nowrap"
                        suppressHydrationWarning
                    >
                        {asOf}
                    </span>
                ) : null}
            </div>
        </section>
    );
}
