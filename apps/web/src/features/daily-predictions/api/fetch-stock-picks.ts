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

    const { data: picks, error: pError } = await db
        .from('daily_stock_picks')
        .select('*')
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

    return (baskets as DailyStockBasket[]).map((b) => ({
        ...b,
        picks: picksByBasket.get(b.id) || [],
    }));
}
