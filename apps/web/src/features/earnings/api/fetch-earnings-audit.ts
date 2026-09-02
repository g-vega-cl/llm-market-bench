import { getSupabaseServerClient } from '~/lib/supabase';

export interface EarningsAlphaSnapshot {
    id: string;
    snapshot_date: string;
    ticker: string;
    sector: string;
    report_date: string | null;
    actual_eps: number | null;
    estimated_eps: number | null;
    eps_surprise: number | null;
    revenue_actual: number | null;
    revenue_estimated: number | null;
    revenue_surprise_pct: number | null;
    sue_score: number | null;
    is_top_decile_sue: boolean;
    quarters_analyzed_count: number;
    has_sufficient_earnings_history: boolean;
    sloan_accrual_ratio: number | null;
    is_sloan_accrual_clean: boolean;
    has_extreme_pre_earnings_runup: boolean;
    pre_earnings_20d_return_pct: number | null;
    days_since_earnings_report: number | null;
    post_earnings_drift_pct: number | null;
    post_earnings_alpha_vs_spy: number | null;
    analyst_consensus: string | null;
    analyst_coverage_count: number;
    analyst_buy_ratio_pct: number | null;
    target_consensus_price: number | null;
    target_consensus_upside_pct: number | null;
}

export interface SectorBellwetherSignal {
    id: string;
    snapshot_date: string;
    sector: string;
    ticker: string;
    classification: string;
    market_cap: number | null;
    market_cap_rank: number | null;
    report_date: string | null;
    cycle_report_day: number | null;
    is_reported: boolean;
    is_active_bellwether_signal: boolean;
    sue_score: number | null;
    revenue_surprise_pct: number | null;
    operating_margin_surprise_delta: number | null;
}

/**
 * Fetches the latest earnings alpha snapshots across all tracked tickers.
 */
export async function fetchEarningsAlphaSnapshots(): Promise<EarningsAlphaSnapshot[]> {
    try {
        const supabase = getSupabaseServerClient();
        const { data, error } = await supabase
            .from('earnings_alpha_snapshots')
            .select('*')
            .order('sue_score', { ascending: false });

        if (error) {
            console.error('Error fetching earnings alpha snapshots:', error);
            return [];
        }

        return (data || []) as EarningsAlphaSnapshot[];
    } catch (err) {
        console.warn('Network or database timeout fetching earnings alpha snapshots:', err);
        return [];
    }
}

/**
 * Fetches sector bellwether signals and peer status.
 */
export async function fetchSectorBellwethers(): Promise<SectorBellwetherSignal[]> {
    try {
        const supabase = getSupabaseServerClient();
        const { data, error } = await supabase
            .from('sector_bellwether_signals')
            .select('*')
            .order('sector', { ascending: true })
            .order('market_cap_rank', { ascending: true });

        if (error) {
            console.error('Error fetching sector bellwethers:', error);
            return [];
        }

        return (data || []) as SectorBellwetherSignal[];
    } catch (err) {
        console.warn('Network or database timeout fetching sector bellwethers:', err);
        return [];
    }
}
