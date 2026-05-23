import { getSupabaseBrowserClient } from '~/lib/supabase-client';

export interface PairHistoryPoint {
    run_date: string;
    pearson_corr: number | null;
    spearman_corr: number | null;
    returns_a_90d: number | null;
    returns_b_90d: number | null;
}

export async function fetchPairHistory(
    tickerA: string,
    tickerB: string,
): Promise<PairHistoryPoint[]> {
    const supabase = getSupabaseBrowserClient();

    // Query correlation_data joining with correlation_runs for run_date.
    // Since the database stores pairs as either order depending on the pipeline execution,
    // we query both combinations using a bidirectional OR logic.
    const { data, error } = await supabase
        .from('correlation_data')
        .select(`
            ticker_a,
            ticker_b,
            pearson_corr,
            spearman_corr,
            returns_a_90d,
            returns_b_90d,
            correlation_runs!inner (
                run_date
            )
        `)
        .or(
            `and(ticker_a.eq.${tickerA},ticker_b.eq.${tickerB}),and(ticker_a.eq.${tickerB},ticker_b.eq.${tickerA})`,
        );

    if (error) {
        throw error;
    }

    if (!data || data.length === 0) {
        return [];
    }

    interface DBHistoryRow {
        ticker_a: string;
        ticker_b: string;
        pearson_corr: number | null;
        spearman_corr: number | null;
        returns_a_90d: number | null;
        returns_b_90d: number | null;
        correlation_runs: { run_date: string } | { run_date: string }[] | null;
    }

    // Map and align returns to match user's requested order of tickerA and tickerB
    const points = (data as unknown as DBHistoryRow[]).map((d) => {
        const isAligned = d.ticker_a === tickerA;
        const runs = d.correlation_runs;
        const runDate = Array.isArray(runs) ? runs[0]?.run_date : runs?.run_date;
        return {
            run_date: runDate || '',
            pearson_corr: d.pearson_corr,
            spearman_corr: d.spearman_corr,
            returns_a_90d: isAligned ? d.returns_a_90d : d.returns_b_90d,
            returns_b_90d: isAligned ? d.returns_b_90d : d.returns_a_90d,
        };
    });

    // Sort chronologically by date
    points.sort((x, y) => new Date(x.run_date).getTime() - new Date(y.run_date).getTime());

    return points;
}
