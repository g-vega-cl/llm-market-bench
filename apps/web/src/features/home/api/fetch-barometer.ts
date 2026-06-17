import type { MarketBarometer } from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';

/**
 * Fetches the latest S&P 500 Market Health Barometer snapshot from the database.
 */
export async function fetchLatestMarketBarometer(): Promise<MarketBarometer | null> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('market_barometer_history')
        .select('*')
        .order('date', { ascending: false })
        .limit(1);

    if (error) {
        console.error('Error fetching latest market barometer:', error);
        return null;
    }

    return (data?.[0] || null) as MarketBarometer | null;
}
