import { getSupabaseServerClient } from '~/lib/supabase';

export interface EarningsPrediction {
    id: string;
    prediction_date: string;
    target_date: string;
    ticker: string;
    model_name: string;
    prompt_variant_tag: string | null;
    predicted_direction: 'UP' | 'DOWN';
    confidence: number;
    expected_return_pct: number | null;
    rationale: string | null;
    catalysts: string[] | null;
    report_timing: 'BMO' | 'AMC' | 'UNKNOWN';
    actual_eps: number | null;
    estimated_eps: number | null;
    eps_surprise: number | null;
    revenue_surprise_pct: number | null;
    sue_score: number | null;
    open_price: number | null;
    close_price: number | null;
    actual_direction: 'UP' | 'DOWN' | null;
    is_correct: boolean | null;
    brier_score: number | null;
    status: 'pending' | 'evaluated';
    created_at: string;
}

/**
 * Fetches Day-1 earnings predictions across models ordered by target_date descending.
 */
export async function fetchEarningsPredictions(limit = 100): Promise<EarningsPrediction[]> {
    try {
        const supabase = getSupabaseServerClient();
        const { data, error } = await supabase
            .from('earnings_predictions')
            .select('*')
            .order('target_date', { ascending: false })
            .limit(limit);

        if (error) {
            console.error('Error fetching earnings predictions:', error);
            return [];
        }

        return (data as EarningsPrediction[]) || [];
    } catch (err) {
        console.error('Exception fetching earnings predictions:', err);
        return [];
    }
}
