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

/**
 * Fetches all available historical barometer dates.
 */
export async function fetchMarketBarometerDates(): Promise<string[]> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('market_barometer_history')
        .select('date')
        .order('date', { ascending: false });

    if (error) {
        console.error('Error fetching market barometer dates:', error);
        return [];
    }

    return (data || []).map((row) => row.date);
}

/**
 * Fetches the market barometer snapshot for a specific date.
 */
export async function fetchMarketBarometerForDate(date: string): Promise<MarketBarometer | null> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('market_barometer_history')
        .select('*')
        .eq('date', date)
        .maybeSingle();

    if (error) {
        console.error(`Error fetching market barometer for date ${date}:`, error);
        return null;
    }

    return data as MarketBarometer | null;
}
