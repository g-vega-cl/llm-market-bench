import { createServerFn } from '@tanstack/react-start';
import { getDbAdminClient } from '~/lib/db';

export interface PublicBoardAction {
    action: string;
    ticker: string;
    price?: number;
    reason?: string;
}

export interface PublicBoardCard {
    recipeId: string;
    name: string;
    returnPct: number | null;
    spyReturnPct: number | null;
    tradeCount: number;
    openPositions: number;
    runsToday: number;
    lastRunAt: string | null;
    lastAction: PublicBoardAction | null;
    resolvedModel: string | null;
}

export interface PublicDeskFeedItem {
    at: string;
    recipeId: string;
    recipeName: string;
    action: string;
    ticker: string;
}

export interface PublicDesk {
    cards: PublicBoardCard[];
    feed: PublicDeskFeedItem[];
    liveCount: number;
    beatSpyCount: number;
    medianReturnPct: number | null;
}

function toNumber(value: unknown): number | null {
    if (value === null || value === undefined) return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
}

export async function fetchPublicDesk(): Promise<PublicDesk> {
    const db = getDbAdminClient();

    const { data, error } = await db
        .from('recipe_public_stats')
        .select(
            'recipe_id, name, return_pct, spy_return_pct, trade_count, open_positions, runs_today, last_run_at, last_action, resolved_model',
        )
        .eq('is_live', true)
        .order('last_run_at', { ascending: false })
        .limit(60);

    if (error) throw new Error(error.message);

    const rows = (data || []) as Array<Record<string, unknown>>;
    const cards: PublicBoardCard[] = rows.map((row) => {
        const action = row.last_action as PublicBoardAction | null;
        return {
            recipeId: String(row.recipe_id),
            name: String(row.name || 'Untitled Strategy'),
            returnPct: toNumber(row.return_pct),
            spyReturnPct: toNumber(row.spy_return_pct),
            tradeCount: Number(row.trade_count || 0),
            openPositions: Number(row.open_positions || 0),
            runsToday: Number(row.runs_today || 0),
            lastRunAt: (row.last_run_at as string | null) ?? null,
            lastAction: action && action.ticker ? action : null,
            resolvedModel: (row.resolved_model as string | null) ?? null,
        };
    });

    const [summaryResult, feedResult] = await Promise.all([
        db
            .from('recipe_desk_summary')
            .select('live_count, beat_spy_count, median_return_pct')
            .eq('id', 1)
            .maybeSingle(),
        db
            .from('recipe_desk_feed')
            .select('recipe_id, recipe_name, action, ticker, at')
            .order('at', { ascending: false })
            .limit(24),
    ]);

    const summary = (summaryResult.data || {}) as Record<string, unknown>;
    const feed: PublicDeskFeedItem[] = (
        (feedResult.data || []) as Array<Record<string, unknown>>
    ).map((row) => ({
        at: String(row.at || ''),
        recipeId: String(row.recipe_id || ''),
        recipeName: String(row.recipe_name || ''),
        action: String(row.action || '').toUpperCase(),
        ticker: String(row.ticker || '').toUpperCase(),
    }));

    return {
        cards,
        feed,
        // Header numbers come from the runner, never from the page: a truncated
        // card list must not masquerade as the live count.
        liveCount: Number(summary.live_count ?? cards.length),
        beatSpyCount: Number(summary.beat_spy_count ?? 0),
        medianReturnPct: toNumber(summary.median_return_pct),
    };
}

export const fetchPublicDeskFn = createServerFn({ method: 'GET' }).handler(fetchPublicDesk);
