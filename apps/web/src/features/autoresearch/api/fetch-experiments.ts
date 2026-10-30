import type { PromptExperiment } from '@llm-market-bench/database';
import { getDbServerClient } from '~/lib/db';

/**
 * Fetch all prompt experiments from the database.
 * Sorted by creation date (descending) to show newest first.
 *
 * This function is intended to be used within a TanStack Start server function.
 */
export async function fetchExperiments(): Promise<PromptExperiment[]> {
    const supabase = getDbServerClient();
    const { data, error } = await supabase
        .from('prompt_experiments')
        .select('*')
        .eq('prompt_name', 'CORE_ANALYSIS_SYSTEM_PROMPT')
        .eq('is_backtest', false)
        .order('created_at', { ascending: false });

    if (error) {
        console.error('Error fetching prompt experiments:', error);
        throw new Error(error.message);
    }

    return (data || []) as PromptExperiment[];
}

/**
 * Fetch all backtest prompt experiments from the database.
 * Sorted by creation date (descending) to show newest first.
 *
 * This function is intended to be used within a TanStack Start server function.
 */
export async function fetchBacktestExperiments(): Promise<PromptExperiment[]> {
    const supabase = getDbServerClient();
    const { data, error } = await supabase
        .from('prompt_experiments')
        .select('*')
        .eq('prompt_name', 'CORE_ANALYSIS_SYSTEM_PROMPT')
        .eq('is_backtest', true)
        .order('created_at', { ascending: false });

    if (error) {
        console.error('Error fetching backtest experiments:', error);
        throw new Error(error.message);
    }

    return (data || []) as PromptExperiment[];
}
