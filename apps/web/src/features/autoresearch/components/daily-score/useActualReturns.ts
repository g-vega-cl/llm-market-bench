import modelsConfig from '@repo/config/models.json';
import { useCallback, useEffect, useRef, useState } from 'react';
import { getDbBrowserClient } from '~/lib/db';
import {
    type ActualReturns,
    calculateSpyReturn,
    getProcessedActualReturns,
    type PortfolioDetail,
} from './daily-score-math';

/**
 * Single discriminated union for /autoresearch live returns so stale data and
 * errors (data != null && error != null) are unrepresentable.
 */
export type ActualsState =
    | { status: 'idle' }
    | { status: 'loading' }
    | { status: 'ready'; actualReturns: ActualReturns | null; actualSpyReturn: number | null }
    | { status: 'error'; error: string };

export async function fetchPortfolioPerformanceData(
    portfolioIds: string[],
    weekStart: string,
    weekEnd: string,
    ownerIds?: string[],
) {
    if (portfolioIds.length === 0 && (!ownerIds || ownerIds.length === 0)) return null;
    const supabase = getDbBrowserClient();
    let query = supabase
        .from('portfolio_performance')
        .select('portfolio_id, total_equity, date, portfolios!inner(owner_id)')
        .gte('date', weekStart)
        .lte('date', weekEnd);

    if (portfolioIds.length > 0) {
        query = query.in('portfolio_id', portfolioIds);
    } else if (ownerIds && ownerIds.length > 0) {
        query = query.in('portfolios.owner_id', ownerIds);
    }

    const { data, error } = await query.order('date', { ascending: true });

    if (error) {
        throw error;
    }
    return data;
}

export async function fetchActiveWeekData(
    portfolioIds: string[],
    weekStart: string,
    weekEnd: string,
    isActive: boolean,
    ownerIds?: string[],
) {
    const supabase = getDbBrowserClient();
    const [portfolioRows, spyRes] = await Promise.all([
        fetchPortfolioPerformanceData(portfolioIds, weekStart, weekEnd, ownerIds),
        isActive
            ? supabase
                  .from('price_history')
                  .select('fetched_at, price')
                  .eq('ticker', 'SPY')
                  .gte('fetched_at', weekStart)
                  .lte('fetched_at', `${weekEnd}T23:59:59`)
                  .order('fetched_at', { ascending: true })
            : Promise.resolve({ data: null, error: null }),
    ]);

    if (spyRes.error) {
        throw spyRes.error;
    }
    return [portfolioRows, spyRes] as const;
}

async function fetchResolvedActuals(args: {
    portfolioIds: string[];
    weekStart: string;
    weekEnd: string;
    isActive: boolean;
    trackId?: string | null;
}): Promise<{ actualReturns: ActualReturns | null; actualSpyReturn: number | null }> {
    const tracks =
        (modelsConfig as { AUTORESEARCH_TRACKS?: Record<string, string[]> }).AUTORESEARCH_TRACKS ||
        {};
    const ownerIds =
        args.portfolioIds.length === 0 ? tracks[args.trackId || 'track_default'] || [] : [];

    const [data, spyRes] = await fetchActiveWeekData(
        args.portfolioIds,
        args.weekStart,
        args.weekEnd,
        args.isActive,
        ownerIds,
    );

    const actualSpyReturn =
        spyRes.data && spyRes.data.length >= 2
            ? calculateSpyReturn(spyRes.data as { price: number | string }[])
            : null;
    const actualReturns = data && data.length > 0 ? getProcessedActualReturns(data) : null;

    return { actualReturns, actualSpyReturn };
}

function extractErrorMessage(err: unknown): string {
    if (err instanceof Error && err.message) {
        return err.message;
    }
    return 'Unable to load live portfolio and benchmark returns.';
}

export function useActualReturns(
    weekStart?: string | null,
    weekEnd?: string | null,
    portfolioDetails?: Record<string, PortfolioDetail> | null,
    isActive?: boolean,
    trackId?: string | null,
) {
    const [state, setState] = useState<ActualsState>(() =>
        weekStart && weekEnd ? { status: 'loading' } : { status: 'idle' },
    );
    const requestSeqRef = useRef(0);
    const isMountedRef = useRef(true);

    const portfolioIdsKey = Object.keys(portfolioDetails || {})
        .sort()
        .join(',');

    const loadActuals = useCallback(async () => {
        const requestSeq = ++requestSeqRef.current;
        if (!weekStart || !weekEnd) {
            setState({ status: 'idle' });
            return;
        }

        const isCurrent = () => isMountedRef.current && requestSeqRef.current === requestSeq;
        const portfolioIds = portfolioIdsKey ? portfolioIdsKey.split(',') : [];

        setState({ status: 'loading' });

        try {
            const resolved = await fetchResolvedActuals({
                portfolioIds,
                weekStart,
                weekEnd,
                isActive: Boolean(isActive),
                trackId,
            });
            if (isCurrent()) {
                setState({ status: 'ready', ...resolved });
            }
        } catch (e) {
            console.error('Failed to load actual returns:', e);
            if (isCurrent()) {
                setState({ status: 'error', error: extractErrorMessage(e) });
            }
        }
    }, [weekStart, weekEnd, portfolioIdsKey, isActive, trackId]);

    useEffect(() => {
        isMountedRef.current = true;
        void loadActuals();
        return () => {
            isMountedRef.current = false;
        };
    }, [loadActuals]);

    const retryActuals = useCallback(() => {
        void loadActuals();
    }, [loadActuals]);

    return {
        actualReturns: state.status === 'ready' ? state.actualReturns : null,
        actualSpyReturn: state.status === 'ready' ? state.actualSpyReturn : null,
        isLoadingActuals: state.status === 'loading',
        actualsError: state.status === 'error' ? state.error : null,
        retryActuals,
    };
}
