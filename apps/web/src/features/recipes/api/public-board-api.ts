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
    /** The sentence the owner described the bot with, when they wrote one. */
    description: string | null;
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

/** A real prompt → compiled-graph example, shown above the fold. */
export interface PublicSpotlight {
    recipeId: string;
    name: string;
    prompt: string;
    blocks: string[];
    returnPct: number | null;
    spyReturnPct: number | null;
}

export interface PublicDesk {
    cards: PublicBoardCard[];
    feed: PublicDeskFeedItem[];
    liveCount: number;
    beatSpyCount: number;
    medianReturnPct: number | null;
    spotlight: PublicSpotlight | null;
}

const BLOCK_LABELS: Record<string, string> = {
    memories: 'Memories',
    news: 'News',
    output_format: 'Output',
    prompt: 'Prompt',
    technicals: 'Technicals',
};

function toNumber(value: unknown): number | null {
    if (value === null || value === undefined) return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
}

/** Distinct block types in graph order, humanised and capped for a chips row. */
export function blockLabels(graph: unknown): string[] {
    const stages = (graph as { stages?: unknown })?.stages;
    if (!Array.isArray(stages)) return [];

    const seen: string[] = [];
    for (const stage of stages) {
        const blocks = (stage as { blocks?: unknown })?.blocks;
        if (!Array.isArray(blocks)) continue;
        for (const block of blocks) {
            const type = String((block as { type?: unknown })?.type ?? '').trim();
            if (!type || seen.includes(type)) continue;
            seen.push(type);
            if (seen.length === 5) break;
        }
    }

    return seen.map((type) => BLOCK_LABELS[type] ?? type.replace(/_/g, ' '));
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

    // The prompt and graph live on the recipe row, not the stats table. A failure
    // here must not cost the desk its cards: degrade to no excerpt.
    const ids = rows.map((row) => String(row.recipe_id));
    const recipeResult =
        ids.length > 0
            ? await db
                  .from('strategy_recipes')
                  .select('id, description, graph_json, updated_at')
                  .in('id', ids)
            : { data: [], error: null };
    const recipes = new Map<string, Record<string, unknown>>();
    if (!recipeResult.error) {
        for (const recipe of (recipeResult.data || []) as Array<Record<string, unknown>>) {
            recipes.set(String(recipe.id), recipe);
        }
    }

    const cards: PublicBoardCard[] = rows.map((row) => {
        const action = row.last_action as PublicBoardAction | null;
        const id = String(row.recipe_id);
        const description = recipes.get(id)?.description;
        return {
            recipeId: id,
            name: String(row.name || 'Untitled Strategy'),
            description:
                typeof description === 'string' && description.trim() ? description.trim() : null,
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

    // Most recently active bot that has a written prompt: that is the proof the
    // page shows, and it must be a real one or nothing.
    const proofCard = cards.find((card) => card.description);
    const proofRecipe = proofCard ? recipes.get(proofCard.recipeId) : undefined;
    const spotlight: PublicSpotlight | null =
        proofCard && proofCard.description
            ? {
                  recipeId: proofCard.recipeId,
                  name: proofCard.name,
                  prompt: proofCard.description,
                  blocks: blockLabels(proofRecipe?.graph_json),
                  returnPct: proofCard.returnPct,
                  spyReturnPct: proofCard.spyReturnPct,
              }
            : null;

    return {
        cards,
        feed,
        // Header numbers come from the runner, never from the page: a truncated
        // card list must not masquerade as the live count.
        liveCount: Number(summary.live_count ?? cards.length),
        beatSpyCount: Number(summary.beat_spy_count ?? 0),
        medianReturnPct: toNumber(summary.median_return_pct),
        spotlight,
    };
}

export const fetchPublicDeskFn = createServerFn({ method: 'GET' }).handler(fetchPublicDesk);
