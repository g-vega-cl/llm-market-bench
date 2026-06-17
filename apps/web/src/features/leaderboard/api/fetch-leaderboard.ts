import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';

export async function fetchLeaderboard(
    timeWindowDays: number | null,
): Promise<LLMLeaderboardRow[]> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase.rpc('get_llm_leaderboard_metrics', {
        time_window_days: timeWindowDays,
    });

    if (error) {
        console.error('Error in fetchLeaderboard:', error);
        throw error;
    }

    return (data || []) as LLMLeaderboardRow[];
}
