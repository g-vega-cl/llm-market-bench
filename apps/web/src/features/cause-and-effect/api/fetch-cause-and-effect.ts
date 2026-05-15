import { getSupabaseBrowserClient } from '~/lib/supabase-client';

export interface CauseAndEffectEntry {
    id: string;
    event?: { content: string };
    analysis: string;
    market_outcome: string;
    confidence: number;
    tags: string[];
    created_at: string;
}

export async function fetchCauseAndEffect(): Promise<CauseAndEffectEntry[]> {
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase
        .from('cause_and_effect')
        .select('*, event:memories(*)')
        .order('created_at', { ascending: false });

    if (error) throw error;
    return data as CauseAndEffectEntry[];
}
