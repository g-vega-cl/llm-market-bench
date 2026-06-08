import type { MarketFeeling } from '@llm-market-bench/database';
import { getSupabaseBrowserClient } from '~/lib/supabase-client';

export interface CorrelationRun {
    id: string;
    run_date: string;
    created_at: string;
    window_days: number;
    num_assets: number;
    tickers: string[];
}

export interface CorrelationData {
    id: string;
    run_id: string;
    ticker_a: string;
    ticker_b: string;
    pearson_corr: number | null;
    spearman_corr: number | null;
    returns_a_90d: number | null;
    returns_b_90d: number | null;
    data_points: number | null;
    returns_a_7d?: number | null;
    returns_b_7d?: number | null;
    returns_a_30d?: number | null;
    returns_b_30d?: number | null;
    returns_a_60d?: number | null;
    returns_b_60d?: number | null;
    pearson_corr_7d?: number | null;
    spearman_corr_7d?: number | null;
    pearson_corr_30d?: number | null;
    spearman_corr_30d?: number | null;
    pearson_corr_60d?: number | null;
    spearman_corr_60d?: number | null;
}

export interface MarketOverviewData {
    correlationRun: CorrelationRun | null;
    correlationData: CorrelationData[];
    marketFeeling: MarketFeeling | null;
}

export async function fetchMarketOverviewData(limit?: number): Promise<MarketOverviewData> {
    const supabase = getSupabaseBrowserClient();

    // Fetch latest correlation run
    const { data: runs, error: runsError } = await supabase
        .from('correlation_runs')
        .select('*')
        .order('run_date', { ascending: false })
        .limit(1);

    if (runsError) throw runsError;

    const correlationRun = runs && runs.length > 0 ? runs[0] : null;

    // Fetch correlation data for the latest run
    let correlationData: CorrelationData[] = [];
    if (correlationRun) {
        let query = supabase.from('correlation_data').select('*').eq('run_id', correlationRun.id);

        if (limit) {
            query = query.limit(limit);
        }

        const { data: corrData, error: corrError } = await query;

        if (corrError) throw corrError;
        correlationData = corrData || [];
    }

    // Fetch latest market feeling
    const { data: feelings, error: feelingsError } = await supabase
        .from('market_feeling')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(1);

    if (feelingsError) throw feelingsError;

    const marketFeeling = feelings && feelings.length > 0 ? feelings[0] : null;

    return {
        correlationRun,
        correlationData,
        marketFeeling,
    };
}
