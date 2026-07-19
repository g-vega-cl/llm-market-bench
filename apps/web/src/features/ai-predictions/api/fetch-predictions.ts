import type { PromptExperiment } from '@llm-market-bench/database';
import { createClient } from '@supabase/supabase-js';

export interface EvaluationAuditItem {
    ticker: string;
    start_price: number;
    end_price: number;
    return_pct: number;
}

export interface EvaluationAuditData {
    start_date: string;
    end_date: string;
    spy?: EvaluationAuditItem | null;
    sector?: EvaluationAuditItem | null;
    pair?: EvaluationAuditItem[] | null;
}

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
    predicted_sector_return?: number | null;
    predicted_pair_return?: number | null;
    benchmark_spy_return?: number | null;
    evaluation_audit_data?: EvaluationAuditData | null;
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

export async function fetchPredictorExperiments(): Promise<PromptExperiment[]> {
    const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
    const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !supabaseKey) {
        throw new Error('Supabase credentials not found');
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data, error } = await supabase
        .from('prompt_experiments')
        .select('*')
        .eq('prompt_name', 'SECTOR_PREDICTOR_PROMPT')
        .order('created_at', { ascending: false });

    if (error) {
        throw new Error(error.message);
    }

    return (data || []) as PromptExperiment[];
}
