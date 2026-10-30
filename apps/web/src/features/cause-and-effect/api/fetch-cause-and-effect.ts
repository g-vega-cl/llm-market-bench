import { getDbBrowserClient } from '~/lib/db';

export interface CauseAndEffectEntry {
    id: string;
    event?: { content: string };
    analysis: string;
    market_outcome: string;
    confidence: number;
    tags: string[];
    created_at: string;
}

export const CAUSE_AND_EFFECT_SELECT = '*, event:memories(id, content, created_at)';

export async function fetchCauseAndEffect(limit?: number): Promise<CauseAndEffectEntry[]> {
    const supabase = getDbBrowserClient();
    let query = supabase
        .from('cause_and_effect')
        .select(CAUSE_AND_EFFECT_SELECT)
        .order('created_at', { ascending: false });

    if (limit) {
        query = query.limit(limit);
    }

    const { data, error } = await query;

    if (error) throw error;
    return data as CauseAndEffectEntry[];
}

export async function fetchCauseAndEffectByEventId(
    eventId: string,
): Promise<CauseAndEffectEntry | null> {
    const supabase = getDbBrowserClient();
    const { data, error } = await supabase
        .from('cause_and_effect')
        .select(CAUSE_AND_EFFECT_SELECT)
        .eq('event_id', eventId)
        .maybeSingle();

    if (error) throw error;
    return data as CauseAndEffectEntry | null;
}
