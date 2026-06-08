import { getSupabaseBrowserClient } from '~/lib/supabase-client';

export interface PairHistoryPoint {
    run_date: string;
    pearson_corr: number | null;
    spearman_corr: number | null;
    returns_a_90d: number | null;
    returns_b_90d: number | null;
    pearson_corr_7d?: number | null;
    spearman_corr_7d?: number | null;
    returns_a_7d?: number | null;
    returns_b_7d?: number | null;
    pearson_corr_30d?: number | null;
    spearman_corr_30d?: number | null;
    returns_a_30d?: number | null;
    returns_b_30d?: number | null;
    pearson_corr_60d?: number | null;
    spearman_corr_60d?: number | null;
    returns_a_60d?: number | null;
    returns_b_60d?: number | null;
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
            pearson_corr_7d,
            spearman_corr_7d,
            returns_a_7d,
            returns_b_7d,
            pearson_corr_30d,
            spearman_corr_30d,
            returns_a_30d,
            returns_b_30d,
            pearson_corr_60d,
            spearman_corr_60d,
            returns_a_60d,
            returns_b_60d,
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
        pearson_corr_7d: number | null;
        spearman_corr_7d: number | null;
        returns_a_7d: number | null;
        returns_b_7d: number | null;
        pearson_corr_30d: number | null;
        spearman_corr_30d: number | null;
        returns_a_30d: number | null;
        returns_b_30d: number | null;
        pearson_corr_60d: number | null;
        spearman_corr_60d: number | null;
        returns_a_60d: number | null;
        returns_b_60d: number | null;
        correlation_runs: { run_date: string } | { run_date: string }[] | null;
    }

    function getAlignedReturns(
        isAligned: boolean,
        valA: number | null,
        valB: number | null,
    ): { a: number | null; b: number | null } {
        return isAligned ? { a: valA, b: valB } : { a: valB, b: valA };
    }

    // Map and align returns to match user's requested order of tickerA and tickerB
    const points = (data as unknown as DBHistoryRow[]).map((d) => {
        const isAligned = d.ticker_a === tickerA;
        const runs = d.correlation_runs;
        const runDate = Array.isArray(runs) ? runs[0]?.run_date : runs?.run_date;
        const ret90 = getAlignedReturns(isAligned, d.returns_a_90d, d.returns_b_90d);
        const ret7 = getAlignedReturns(isAligned, d.returns_a_7d, d.returns_b_7d);
        const ret30 = getAlignedReturns(isAligned, d.returns_a_30d, d.returns_b_30d);
        const ret60 = getAlignedReturns(isAligned, d.returns_a_60d, d.returns_b_60d);

        return {
            run_date: runDate || '',
            pearson_corr: d.pearson_corr,
            spearman_corr: d.spearman_corr,
            returns_a_90d: ret90.a,
            returns_b_90d: ret90.b,
            pearson_corr_7d: d.pearson_corr_7d,
            spearman_corr_7d: d.spearman_corr_7d,
            returns_a_7d: ret7.a,
            returns_b_7d: ret7.b,
            pearson_corr_30d: d.pearson_corr_30d,
            spearman_corr_30d: d.spearman_corr_30d,
            returns_a_30d: ret30.a,
            returns_b_30d: ret30.b,
            pearson_corr_60d: d.pearson_corr_60d,
            spearman_corr_60d: d.spearman_corr_60d,
            returns_a_60d: ret60.a,
            returns_b_60d: ret60.b,
        };
    });

    // Sort chronologically by date
    points.sort((x, y) => new Date(x.run_date).getTime() - new Date(y.run_date).getTime());

    return points;
}
