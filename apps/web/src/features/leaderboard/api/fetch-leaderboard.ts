import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import { MODELS } from '~/config/models';
import { getSupabaseServerClient } from '~/lib/supabase';

const activeModels = new Set<string>(Object.values(MODELS));

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

    const rows = (data || []) as LLMLeaderboardRow[];
    return rows.filter((row) => activeModels.has(row.model_name));
}
