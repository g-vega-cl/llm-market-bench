import type { PromptExperiment } from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';

/**
 * Fetch all prompt experiments from the database.
 * Sorted by creation date (descending) to show newest first.
 *
 * This function is intended to be used within a TanStack Start server function.
 */
export async function fetchExperiments(): Promise<PromptExperiment[]> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('prompt_experiments')
        .select('*')
        .order('created_at', { ascending: false });

    if (error) {
        console.error('Error fetching prompt experiments:', error);
        throw new Error(error.message);
    }

    return (data || []) as PromptExperiment[];
}
