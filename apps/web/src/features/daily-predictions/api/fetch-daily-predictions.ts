import type { PromptExperiment } from '@llm-market-bench/database';
import { createClient } from '@supabase/supabase-js';

export interface DailyPrediction {
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
    open_price: number | null;
    high_price?: number | null;
    low_price?: number | null;
    close_price: number | null;
    actual_direction: 'UP' | 'DOWN' | null;
    is_correct: boolean | null;
    intraday_hit?: boolean | null;
    intraday_direction_hit?: boolean | null;
    brier_score: number | null;
    status: 'pending' | 'evaluated';
    created_at: string;
    updated_at: string;
}

export async function fetchDailyPredictions(): Promise<DailyPrediction[]> {
    const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
    const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !supabaseKey) {
        throw new Error('Supabase credentials not found');
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data, error } = await supabase
        .from('daily_predictions')
        .select('*')
        .order('created_at', { ascending: false });

    if (error) {
        throw new Error(error.message);
    }

    return (data || []) as DailyPrediction[];
}

export async function fetchDailyPredictorExperiments(): Promise<PromptExperiment[]> {
    const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
    const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !supabaseKey) {
        throw new Error('Supabase credentials not found');
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data, error } = await supabase
        .from('prompt_experiments')
        .select('*')
        .eq('prompt_name', 'DAILY_PREDICTOR_PROMPT')
        .eq('is_backtest', false)
        .order('created_at', { ascending: false });

    if (error) {
        throw new Error(error.message);
    }

    return (data || []) as PromptExperiment[];
}

export async function fetchDailyPredictorBacktestExperiments(): Promise<PromptExperiment[]> {
    const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
    const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !supabaseKey) {
        throw new Error('Supabase credentials not found');
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data, error } = await supabase
        .from('prompt_experiments')
        .select('*')
        .eq('prompt_name', 'DAILY_PREDICTOR_PROMPT')
        .eq('is_backtest', true)
        .order('created_at', { ascending: false });

    if (error) {
        throw new Error(error.message);
    }

    return (data || []) as PromptExperiment[];
}

export async function fetchDailyPredictorBacktestPredictions(): Promise<DailyPrediction[]> {
    const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
    const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !supabaseKey) {
        throw new Error('Supabase credentials not found');
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data, error } = await supabase
        .from('daily_predictions')
        .select('*')
        .ilike('prompt_variant_tag', '%backtest%')
        .order('created_at', { ascending: false });

    if (error) {
        // Fallback: return all predictions if ilike query fails or is empty
        const { data: allData } = await supabase
            .from('daily_predictions')
            .select('*')
            .order('created_at', { ascending: false });
        return (allData || []) as DailyPrediction[];
    }

    return (data || []) as DailyPrediction[];
}
