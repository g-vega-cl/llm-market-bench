import { getDbServerClient } from '~/lib/db';

export interface DailyStockPick {
    id: string;
    basket_id: string;
    target_date: string;
    model_name: string;
    ticker: string;
    direction: 'UP' | 'DOWN';
    rank: number;
    confidence: number;
    expected_return_pct: number | null;
    reasoning: string | null;
    status: 'pending' | 'evaluated' | 'cancelled';
    open_price: number | null;
    close_price: number | null;
    stock_return_pct: number | null;
    position_return_pct: number | null;
    is_hit: boolean | null;
    conviction_points: number | null;
    created_at: string;
    evaluated_at: string | null;
}

export interface DailyStockBasket {
    id: string;
    target_date: string;
    model_name: string;
    status: 'pending' | 'evaluated' | 'cancelled';
    directional_hit_rate: number | null;
    mean_long_return_pct: number | null;
    mean_short_return_pct: number | null;
    ls_spread_alpha_pct: number | null;
    excess_alpha_vs_spy_pct: number | null;
    benchmark_spy_return_pct: number | null;
    created_at: string;
    evaluated_at: string | null;
    picks?: DailyStockPick[];
}

/**
 * Newest basket id per model track. `baskets` must be ordered newest-first.
 *
 * Only the latest basket of each track is rendered as a 3 UP / 3 DOWN card set;
 * the history table reads basket metrics only. Fetching picks for every basket
 * would grow the payload unbounded with nothing to render them.
 */
export function latestBasketIdsByModel(baskets: DailyStockBasket[]): string[] {
    const seen = new Set<string>();
    const ids: string[] = [];
    for (const basket of baskets) {
        if (seen.has(basket.model_name)) continue;
        seen.add(basket.model_name);
        ids.push(basket.id);
    }
    return ids;
}

export async function fetchDailyStockBaskets(): Promise<DailyStockBasket[]> {
    const db = getDbServerClient();

    const { data: baskets, error: bError } = await db
        .from('daily_stock_baskets')
        .select('*')
        .order('target_date', { ascending: false });

    if (bError) {
        throw new Error(bError.message);
    }

    if (!baskets || baskets.length === 0) {
        return [];
    }

    const typedBaskets = baskets as DailyStockBasket[];
    const latestBasketIds = latestBasketIdsByModel(typedBaskets);

    // Scoped to the newest basket per track so the pick scan stays bounded by
    // model count instead of growing with every historical session.
    const { data: picks, error: pError } = await db
        .from('daily_stock_picks')
        .select('*')
        .in('basket_id', latestBasketIds)
        .order('rank', { ascending: true });

    if (pError) {
        throw new Error(pError.message);
    }

    const picksByBasket = new Map<string, DailyStockPick[]>();
    for (const p of (picks || []) as DailyStockPick[]) {
        const existing = picksByBasket.get(p.basket_id) || [];
        existing.push(p);
        picksByBasket.set(p.basket_id, existing);
    }

    return typedBaskets.map((b) => ({
        ...b,
        picks: picksByBasket.get(b.id) || [],
    }));
}
