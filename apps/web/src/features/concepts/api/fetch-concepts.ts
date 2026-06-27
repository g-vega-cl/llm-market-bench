import { getSupabaseServerClient } from '~/lib/supabase';
import type { Concept } from '../components/ConceptMap';

export type { Concept };

export interface ConceptMemory {
    id: string;
    content: string;
    // biome-ignore lint/suspicious/noExplicitAny: metadata is a custom JSON object from DB
    metadata: { impact?: string; [key: string]: any } | null;
    similarity: number;
    created_at?: string | null;
}

export async function fetchConcepts(): Promise<Concept[]> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('concept_metrics')
        .select(
            'id, concept_name, pca_x, pca_y, mention_count, velocity_score, first_mention_at, last_mention_at',
        )
        .not('pca_x', 'is', null)
        .limit(1000);

    if (error) {
        console.error('Error fetching concepts:', error);
        return [];
    }
    return data as Concept[];
}

export async function fetchConceptMemories(conceptId: string): Promise<ConceptMemory[]> {
    const supabase = getSupabaseServerClient();

    // 1. Fetch the concept vector
    const { data: conceptData, error: conceptError } = await supabase
        .from('concept_metrics')
        .select('concept_vector')
        .eq('id', conceptId)
        .single();

    if (conceptError || !conceptData?.concept_vector) {
        console.error('Error fetching concept vector:', conceptError);
        return [];
    }

    // 2. Query similar memories
    const { data: memoriesData, error: memoriesError } = await supabase.rpc('match_memories', {
        query_embedding: conceptData.concept_vector,
        match_threshold: 0.3,
        match_count: 5,
    });

    if (memoriesError) {
        console.error('Error fetching matching memories:', memoriesError);
        return [];
    }

    if (!memoriesData || memoriesData.length === 0) {
        return [];
    }

    // 3. Fetch created_at timestamps for matching memories
    const memoryIds = memoriesData.map((m: { id: string }) => m.id);
    const { data: details } = await supabase
        .from('memories')
        .select('id, created_at')
        .in('id', memoryIds);

    const dateMap = new Map((details || []).map((d) => [d.id, d.created_at]));

    return memoriesData.map((m: ConceptMemory) => ({
        ...m,
        created_at: dateMap.get(m.id) ?? null,
    }));
}
