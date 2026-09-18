import { useEffect, useState } from 'react';
import { getSupabaseBrowserClient } from '~/lib/supabase-client';
import {
    type ActualReturns,
    calculateSpyReturn,
    getProcessedActualReturns,
    type PortfolioDetail,
} from './daily-score-math';

export async function fetchPortfolioPerformanceData(
    portfolioIds: string[],
    weekStart: string,
    weekEnd: string,
) {
    if (portfolioIds.length === 0) return null;
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase
        .from('portfolio_performance')
        .select('portfolio_id, total_equity, date, portfolios!inner(owner_id)')
        .in('portfolio_id', portfolioIds)
        .gte('date', weekStart)
        .lte('date', weekEnd)
        .order('date', { ascending: true });

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
) {
    const supabase = getSupabaseBrowserClient();
    return Promise.all([
        fetchPortfolioPerformanceData(portfolioIds, weekStart, weekEnd),
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
}

export function processSpyResponse(
    spyRes: { data: unknown[] | null },
    isMounted: boolean,
    setActualSpyReturn: (r: number) => void,
) {
    if (spyRes.data && spyRes.data.length >= 2) {
        const computedReturn = calculateSpyReturn(spyRes.data as { price: number | string }[]);
        if (isMounted) {
            setActualSpyReturn(computedReturn);
        }
    }
}

export function processPortfolioData(
    data: unknown[] | null,
    isMounted: boolean,
    setActualReturns: (r: ActualReturns) => void,
) {
    if (data && data.length > 0) {
        const results = getProcessedActualReturns(data);
        if (isMounted) {
            setActualReturns(results);
        }
    }
}

export function useActualReturns(
    weekStart?: string | null,
    weekEnd?: string | null,
    portfolioDetails?: Record<string, PortfolioDetail> | null,
    isActive?: boolean,
) {
    const [actualReturns, setActualReturns] = useState<ActualReturns | null>(null);
    const [actualSpyReturn, setActualSpyReturn] = useState<number | null>(null);
    const [isLoadingActuals, setIsLoadingActuals] = useState(false);

    useEffect(() => {
        if (!weekStart || !weekEnd) return;
        const details = portfolioDetails || {};
        const portfolioIds = Object.keys(details);

        let isMounted = true;
        setIsLoadingActuals(true);

        const loadActuals = async () => {
            try {
                const [data, spyRes] = await fetchActiveWeekData(
                    portfolioIds,
                    weekStart,
                    weekEnd,
                    !!isActive,
                );

                processSpyResponse(spyRes, isMounted, setActualSpyReturn);
                processPortfolioData(data, isMounted, setActualReturns);
            } catch (e) {
                console.error('Failed to load actual returns:', e);
            } finally {
                if (isMounted) {
                    setIsLoadingActuals(false);
                }
            }
        };

        loadActuals();
        return () => {
            isMounted = false;
        };
    }, [weekStart, weekEnd, portfolioDetails, isActive]);

    return { actualReturns, actualSpyReturn, isLoadingActuals };
}
