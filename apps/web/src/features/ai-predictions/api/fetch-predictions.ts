import type { PromptExperiment } from '@llm-market-bench/database';
import { getDbServerClient } from '~/lib/db';

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
    worst_sector?: EvaluationAuditItem | null;
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
    predicted_worst_sector?: string | null;
    predicted_pair: string[];
    confidence?: number | null;
    brier_score?: number | null;
    reasoning: string;
    sector_percentile_score: number | null;
    worst_sector_percentile_score?: number | null;
    pair_percentile_score: number | null;
    predicted_sector_return?: number | null;
    predicted_worst_sector_return?: number | null;
    predicted_pair_return?: number | null;
    benchmark_spy_return?: number | null;
    sector_sp_diff?: number | null;
    evaluation_audit_data?: EvaluationAuditData | null;
    status: 'pending' | 'evaluated';
    created_at: string;
}

export async function fetchAIPredictions(): Promise<SectorPrediction[]> {
    const db = getDbServerClient();

    const { data, error } = await db
        .from('sector_predictions')
        .select('*')
        .order('created_at', { ascending: false });

    if (error) {
        throw new Error(error.message);
    }

    return data as SectorPrediction[];
}

export async function fetchPredictorExperiments(): Promise<PromptExperiment[]> {
    const db = getDbServerClient();

    const { data, error } = await db
        .from('prompt_experiments')
        .select('*')
        .eq('prompt_name', 'SECTOR_PREDICTOR_PROMPT')
        .order('created_at', { ascending: false });

    if (error) {
        throw new Error(error.message);
    }

    return (data || []) as PromptExperiment[];
}
