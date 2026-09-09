import { getSupabaseServerClient } from '~/lib/supabase';
import type { Concept, ConceptCatalyst } from '../components/ConceptMap';

export type { Concept, ConceptCatalyst };

export interface ConceptMemory {
    id: string;
    content: string;
    // biome-ignore lint/suspicious/noExplicitAny: metadata is a custom JSON object from DB
    metadata: { impact?: string; [key: string]: any } | null;
    similarity: number;
    created_at?: string | null;
}

export function parseVector(vec: unknown): number[] | null {
    if (!vec) return null;
    if (Array.isArray(vec)) return vec.map(Number);
    if (typeof vec === 'string') {
        try {
            const parsed = JSON.parse(vec);
            return Array.isArray(parsed) ? parsed.map(Number) : null;
        } catch {
            return null;
        }
    }
    return null;
}

export function calculateDateOffset(
    targetDateStr: string,
    refDate: Date = new Date(),
): {
    deltaDays: number;
    stage: 'upcoming' | 'active' | 'digesting' | 'expired';
    label: string;
} {
    const match = targetDateStr.match(/(\d{4}-\d{2}-\d{2})/);
    if (!match) return { deltaDays: 0, stage: 'expired', label: 'expired' };

    const estDateStr = refDate.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
    const targetDate = new Date(`${match[1]}T00:00:00`);
    const todayDate = new Date(`${estDateStr}T00:00:00`);
    const diffMs = targetDate.getTime() - todayDate.getTime();
    const deltaDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

    if (deltaDays > 0) {
        let label = `in ${deltaDays} days`;
        if (deltaDays === 1) label = 'tomorrow';
        else if (deltaDays === 7) label = '1 week from now';
        else if (deltaDays === 14) label = '2 weeks from now';
        else if (deltaDays % 7 === 0 && deltaDays > 14) label = `${deltaDays / 7} weeks from now`;
        return { deltaDays, stage: 'upcoming', label };
    }
    if (deltaDays === 0) {
        return { deltaDays: 0, stage: 'active', label: 'today' };
    }
    if (deltaDays >= -3) {
        const absDays = Math.abs(deltaDays);
        return {
            deltaDays,
            stage: 'digesting',
            label: `digesting, ${absDays} day${absDays > 1 ? 's' : ''} ago`,
        };
    }
    return { deltaDays, stage: 'expired', label: 'expired' };
}

export function cosineSimilarity(vecA: number[], vecB: number[]): number {
    if (!vecA || !vecB || vecA.length !== vecB.length) return 0;
    let dot = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < vecA.length; i++) {
        dot += vecA[i] * vecB[i];
        normA += vecA[i] * vecA[i];
        normB += vecB[i] * vecB[i];
    }
    if (normA === 0 || normB === 0) return 0;
    return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

export function cleanCatalystTitle(content: string): string {
    let title = content.replace(/^\[CALENDAR EVENT\]\s*/i, '');
    title = title.replace(/^\([^)]*\)\s*/, '');
    title = title.replace(/^\d{4}-\d{2}-\d{2}:\s*/, '');
    if (title.includes('|')) {
        title = title.split('|')[0].trim();
    }
    if (title.includes(':')) {
        const parts = title.split(':');
        if (parts[0].trim().length > 3) {
            title = parts[0].trim();
        }
    }
    return title.trim() || content.trim();
}

export interface RadarRow {
    concept_id: string;
    catalyst_id: string;
    catalyst_title: string;
    target_date: string;
    impact?: string;
    similarity?: number;
    memory_content?: string;
    related_tickers?: string[] | unknown;
}

export function mapCatalystsToConcepts(
    concepts: Concept[],
    radarRows: RadarRow[],
    now: Date = new Date(),
): Concept[] {
    if (!radarRows.length) return concepts;

    const catalystMap = new Map<string, ConceptCatalyst>();
    for (const row of radarRows) {
        const dateOffset = calculateDateOffset(row.target_date, now);
        if (dateOffset.stage === 'expired') {
            continue;
        }

        const existing = catalystMap.get(row.concept_id);
        if (existing && Math.abs(existing.days_to_event) <= Math.abs(dateOffset.deltaDays)) {
            continue;
        }

        const tickers = Array.isArray(row.related_tickers) ? (row.related_tickers as string[]) : [];

        catalystMap.set(row.concept_id, {
            catalyst_id: row.catalyst_id,
            catalyst_title: row.catalyst_title,
            target_date: row.target_date,
            days_to_event: dateOffset.deltaDays,
            stage: dateOffset.stage,
            date_offset_label: dateOffset.label,
            impact: row.impact || 'NEUTRAL',
            similarity: Number(row.similarity) || 0,
            memory_content: row.memory_content || '',
            related_tickers: tickers,
        });
    }

    for (const concept of concepts) {
        const cat = catalystMap.get(concept.id);
        if (cat) {
            concept.catalyst = cat;
        }
    }

    return concepts;
}

let cachedConcepts: Concept[] | null = null;
let lastConceptsFetchTime = 0;
const CONCEPTS_CACHE_TTL = 1000 * 60 * 5; // 5 minutes (300,000 ms) server in-memory cache

export function clearConceptsCache() {
    cachedConcepts = null;
    lastConceptsFetchTime = 0;
}

export async function fetchConcepts(options?: { forceFresh?: boolean }): Promise<Concept[]> {
    const nowTime = Date.now();
    if (
        !options?.forceFresh &&
        cachedConcepts &&
        nowTime - lastConceptsFetchTime < CONCEPTS_CACHE_TTL
    ) {
        return cachedConcepts;
    }

    const supabase = getSupabaseServerClient();
    const [conceptsResp, radarResp] = await Promise.all([
        supabase
            .from('concept_metrics')
            .select(
                'id, concept_name, pca_x, pca_y, mention_count, velocity_score, first_mention_at, last_mention_at',
            )
            .not('pca_x', 'is', null)
            .limit(1000),
        supabase
            .from('catalyst_radar')
            .select(
                'concept_id, catalyst_id, catalyst_title, target_date, impact, similarity, memory_content, related_tickers',
            )
            .order('velocity_score', { ascending: false })
            .limit(300),
    ]);

    if (conceptsResp.error) {
        console.error('Error fetching concepts:', conceptsResp.error);
        return [];
    }

    const concepts = (conceptsResp.data || []) as Concept[];
    const radarRows = (radarResp.data || []) as RadarRow[];

    mapCatalystsToConcepts(concepts, radarRows, new Date());

    cachedConcepts = concepts;
    lastConceptsFetchTime = nowTime;
    return concepts;
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
