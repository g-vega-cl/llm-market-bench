import type { BacktestError, RecipeSummaryItem, StrategyRecipeRecord } from '../types';

/**
 * Token refusals are the quota failure now: a run stops because the balance hit
 * zero or the guest budget is spent, not because a daily counter ran out. Both
 * must surface with the capacity CTA, so both classify as quota.
 */
const QUOTA_LIMIT_PATTERN =
    /limit reached|queue is currently full|out of tokens|guest runs are used up/i;

export function isQuotaLimitMessage(message: string): boolean {
    return QUOTA_LIMIT_PATTERN.test(message);
}

/**
 * Build a BacktestError from a caught error during backtest enqueue/navigate.
 * Replaces the old buildExecutionErrorState which handled live_turn + backtest.
 */
export function buildBacktestError(params: {
    err: unknown;
    queuedBacktestJobId?: string;
}): BacktestError {
    const message = params.err instanceof Error ? params.err.message : 'Execution failed';
    if (isQuotaLimitMessage(message)) {
        console.warn('[RecipeStudio] Backtest blocked by quota:', message);
        return { kind: 'quota', message };
    }
    console.error('[RecipeStudio] Backtest failed:', params.err);
    if (params.queuedBacktestJobId) {
        return { kind: 'navigation', message, backtestJobId: params.queuedBacktestJobId };
    }
    return { kind: 'execution', message };
}

function resolveEasternIsoOffset(datePart: string, hmPart: string, secPart: string): string {
    // Probe UTC timestamp against America/New_York to determine EST (-05:00) vs EDT (-04:00).
    const approxUtc = new Date(`${datePart}T${hmPart}:${secPart}Z`);
    const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/New_York',
        timeZoneName: 'shortOffset',
    }).formatToParts(approxUtc);
    const tzPart = parts.find((p) => p.type === 'timeZoneName')?.value ?? 'GMT-5';
    const offsetMatch = /GMT([+-])(\d{1,2})(?::(\d{2}))?/i.exec(tzPart);
    if (!offsetMatch) return '-05:00';
    const [, sign, hrs, mins = '00'] = offsetMatch;
    return `${sign}${hrs.padStart(2, '0')}:${mins.padStart(2, '0')}`;
}

/**
 * Normalize an equity-curve timestamp (e.g. "2026-11-14 09:30 ET" or ISO-8601)
 * into a Date.parse()-safe ISO string.
 */
export function normalizeEquityTimestamp(rawTime: string): string | null {
    const trimmed = String(rawTime || '').trim();
    if (!trimmed) return null;

    const etMatch = /^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})(?::(\d{2}))?\s+ET$/i.exec(trimmed);
    if (etMatch) {
        const [, datePart, hmPart, secPart = '00'] = etMatch;
        const offset = resolveEasternIsoOffset(datePart, hmPart, secPart);
        return `${datePart}T${hmPart}:${secPart}${offset}`;
    }

    if (!Number.isNaN(Date.parse(trimmed))) {
        return trimmed;
    }

    return null;
}

export interface LiveEquitySnapshot {
    date: string;
    total_equity: number;
}

export function toLiveEquitySnapshots(
    equityCurve: { time: string; equity: number }[] | undefined,
): LiveEquitySnapshot[] {
    if (!Array.isArray(equityCurve) || equityCurve.length === 0) return [];
    const parsed: { date: string; total_equity: number; ts: number }[] = [];

    for (const point of equityCurve) {
        if (!point) continue;
        const normalized = normalizeEquityTimestamp(point.time);
        const equity = Number(point.equity);
        if (!normalized || !Number.isFinite(equity)) continue;
        const ts = Date.parse(normalized);
        if (Number.isNaN(ts)) continue;
        parsed.push({ date: normalized, total_equity: equity, ts });
    }

    parsed.sort((a, b) => a.ts - b.ts);
    return parsed.map(({ date, total_equity }) => ({ date, total_equity }));
}

export function upsertSavedRecipeSummary(
    prev: RecipeSummaryItem[],
    saved: StrategyRecipeRecord,
    isLive?: boolean,
): RecipeSummaryItem[] {
    const existing = prev.find((r) => r.id === saved.id);
    const nextLive = isLive ?? existing?.is_live ?? Boolean(saved.is_live);
    const nextTurbo = nextLive ? existing?.turbo_expires_at : null;
    if (!existing) {
        return [
            {
                id: saved.id,
                name: saved.name,
                cadence: saved.cadence,
                is_live: nextLive,
                is_public: Boolean(saved.is_public),
                trial_count: saved.trial_count ?? 0,
                updated_at: saved.updated_at ?? new Date().toISOString(),
                turbo_expires_at: nextTurbo ?? null,
            },
            ...prev,
        ];
    }
    return prev.map((r) =>
        r.id === saved.id
            ? {
                  ...r,
                  name: saved.name,
                  cadence: saved.cadence,
                  is_live: nextLive,
                  turbo_expires_at: nextLive ? (r.turbo_expires_at ?? null) : null,
              }
            : r,
    );
}
