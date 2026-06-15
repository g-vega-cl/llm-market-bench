import { createClient } from '@supabase/supabase-js';

export interface SectorPrediction {
    id: string;
    prediction_date: string;
    target_date: string;
    timeframe: string;
    model_name: string;
    prompt_tag: string;
    predicted_sector: string;
    predicted_pair: string[];
    reasoning: string;
    sector_percentile_score: number | null;
    pair_percentile_score: number | null;
    status: 'pending' | 'evaluated';
    created_at: string;
}

export async function fetchAIPredictions(): Promise<SectorPrediction[]> {
    const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
    const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !supabaseKey) {
        throw new Error('Supabase credentials not found');
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data, error } = await supabase
        .from('sector_predictions')
        .select('*')
        .order('created_at', { ascending: false });

    if (error) {
        throw new Error(error.message);
    }

    return data as SectorPrediction[];
}
