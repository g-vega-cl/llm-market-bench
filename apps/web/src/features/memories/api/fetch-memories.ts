import type { Memory } from '@llm-market-bench/database';
import { getSupabaseBrowserClient } from '~/lib/supabase-client';

const PAGE_SIZE = 50;

export interface PaginatedMemories {
    data: Memory[];
    hasMore: boolean;
    nextCursor: string | null;
}

// biome-ignore lint/suspicious/noExplicitAny: complex Supabase query builder type
function applyCategoryFilter(query: any, category: string) {
    switch (category) {
        case 'MARKET_EVENT':
        case 'consensus_event':
            return query.eq('memory_type', 'MARKET_EVENT');
        case 'CALENDAR_EVENT':
        case 'calendar_event':
            return query.eq('memory_type', 'CALENDAR_EVENT');
        case 'ACADEMIC_PAPER':
        case 'academic_paper':
            return query.eq('memory_type', 'ACADEMIC_PAPER');
        case 'POST_MORTEM':
        case 'post_mortem':
            return query.eq('memory_type', 'POST_MORTEM');
        case 'LESSON_LEARNED':
        case 'lesson_learned':
            return query.eq('memory_type', 'LESSON_LEARNED');
        default:
            return query;
    }
}

export async function fetchMemories(
    cursor?: string,
    pageSize: number = PAGE_SIZE,
    category?: string,
): Promise<PaginatedMemories> {
    const supabase = getSupabaseBrowserClient();

    let query = supabase.from('memories').select('*, parent_id, status, relationship_type');

    if (category && category !== 'all') {
        query = applyCategoryFilter(query, category);
    }

    query = query.order('created_at', { ascending: false }).limit(pageSize + 1);

    if (cursor) {
        query = query.lt('created_at', cursor);
    }

    const { data, error } = await query;

    if (error) throw error;

    const hasMore = data.length > pageSize;
    const paginatedData = hasMore ? data.slice(0, pageSize) : data;

    const nextCursor =
        hasMore && paginatedData.length > 0
            ? paginatedData[paginatedData.length - 1].created_at
            : null;

    return {
        data: paginatedData,
        hasMore,
        nextCursor,
    };
}

export async function fetchAllMemories(): Promise<Memory[]> {
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase
        .from('memories')
        .select('*, parent_id, status, relationship_type')
        .order('created_at', { ascending: false });

    if (error) throw error;
    return data as Memory[];
}

export async function fetchNewMemories(since: string): Promise<Memory[]> {
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase
        .from('memories')
        .select('*, parent_id, status, relationship_type')
        .gt('created_at', since)
        .order('created_at', { ascending: false });

    if (error) throw error;
    return data as Memory[];
}

export interface CacheValidationResult {
    exists: boolean;
    latestTimestamp: string | null;
}

/**
 * Lightweight check to validate a cached memory ID and fetch the absolute newest timestamp.
 * Used for self-healing delta-sync checks on page mount.
 */
export async function validateCacheState(cachedId: string): Promise<CacheValidationResult> {
    const supabase = getSupabaseBrowserClient();

    // 1. Fetch newest timestamp
    const timestampQuery = supabase
        .from('memories')
        .select('created_at')
        .order('created_at', { ascending: false })
        .limit(1);

    // 2. Check if the cached ID still exists
    const existenceQuery = supabase.from('memories').select('id').eq('id', cachedId).limit(1);

    const [tsRes, existRes] = await Promise.all([timestampQuery, existenceQuery]);

    if (tsRes.error) throw tsRes.error;
    if (existRes.error) throw existRes.error;

    const latestTimestamp = tsRes.data && tsRes.data.length > 0 ? tsRes.data[0].created_at : null;
    const exists = existRes.data && existRes.data.length > 0;

    return {
        exists,
        latestTimestamp,
    };
}

export async function fetchMemoryById(memoryId: string): Promise<Memory | null> {
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase
        .from('memories')
        .select('*, parent_id, status, relationship_type')
        .eq('id', memoryId)
        .single();

    if (error) {
        if (error.code === 'PGRST116') {
            return null; // Row not found
        }
        throw error;
    }
    return data as Memory;
}

export async function fetchMemoryChain(memoryId: string): Promise<Memory[]> {
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase.rpc('get_memory_chain', {
        target_id: memoryId,
    });

    if (error) throw error;
    return (data || []) as Memory[];
}

export interface NewsletterSnapshot {
    source_id: string;
    sender: string;
    subject: string;
    content: string;
    date: string;
}

export async function fetchReferencedNewsletters(
    sourceIds: string[],
): Promise<NewsletterSnapshot[]> {
    if (!sourceIds || sourceIds.length === 0) return [];

    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase.rpc('get_referenced_newsletter_snapshots', {
        target_source_ids: sourceIds,
    });

    if (error) throw error;
    return (data || []) as NewsletterSnapshot[];
}

export async function fetchChildResolutionEvent(parentId: string): Promise<Memory | null> {
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase
        .from('memories')
        .select('*, parent_id, status, relationship_type')
        .eq('parent_id', parentId)
        .eq('relationship_type', 'RESOLUTION')
        .maybeSingle();

    if (error) throw error;
    return data as Memory | null;
}

async function loadGeminiApiKey(): Promise<string> {
    if (process.env.GEMINI_API_KEY) {
        return process.env.GEMINI_API_KEY;
    }
    const isServer = typeof window === 'undefined' || process.env.NODE_ENV === 'test';
    if (!isServer) {
        return '';
    }
    try {
        const fs = await import('node:fs');
        const path = await import('node:path');
        const paths = [
            path.resolve(process.cwd(), 'apps/engine/.env'),
            path.resolve(process.cwd(), '.env'),
            path.resolve(process.cwd(), '../../apps/engine/.env'),
            path.resolve(process.cwd(), '../engine/.env'),
        ];
        for (const p of paths) {
            if (fs.existsSync(p)) {
                const content = fs.readFileSync(p, 'utf-8');
                const match = content.match(/^GEMINI_API_KEY=["']?([^"'\r\n]+)["']?/m);
                if (match?.[1]) {
                    return match[1];
                }
            }
        }
    } catch (_e) {
        // Fallback
    }
    return '';
}

async function fetchEmbeddingSingle(url: string, text: string): Promise<number[]> {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: 'models/gemini-embedding-001',
            content: { parts: [{ text }] },
            outputDimensionality: 768,
        }),
    });

    if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Gemini Embedding API returned status ${response.status}: ${errText}`);
    }

    const data = (await response.json()) as {
        embedding?: { values?: number[] };
    };

    const values = data.embedding?.values;
    if (!values || values.length === 0) {
        throw new Error('No embedding values returned from Gemini REST API');
    }

    return values;
}

export async function getGeminiEmbedding(text: string): Promise<number[]> {
    const apiKey = await loadGeminiApiKey();
    if (!apiKey) {
        throw new Error('GEMINI_API_KEY not found in engine .env or environment');
    }

    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key=${apiKey}`;
    const cleanedText = text.replace(/\n/g, ' ');

    let lastError: Error | null = null;
    for (let attempt = 1; attempt <= 3; attempt++) {
        try {
            return await fetchEmbeddingSingle(url, cleanedText);
        } catch (error: unknown) {
            lastError = error instanceof Error ? error : new Error(String(error));
            if (attempt < 3) {
                const delay = 2 ** attempt * 1000;
                await new Promise((resolve) => setTimeout(resolve, delay));
            }
        }
    }

    throw lastError || new Error('Failed to generate embedding after 3 attempts');
}

interface MatchedMemoryRow {
    id: string;
    content: string;
    metadata: Record<string, unknown> | null;
    similarity: number;
}

export async function searchMemories(
    queryText: string,
    limit: number = 50,
    threshold: number = 0.4,
): Promise<Memory[]> {
    const embedding = await getGeminiEmbedding(queryText);
    const supabase = getSupabaseBrowserClient();

    // Call match_memories RPC
    const { data, error: rpcError } = await supabase.rpc('match_memories', {
        query_embedding: embedding,
        match_threshold: threshold,
        match_count: limit,
    });

    if (rpcError) throw rpcError;
    const matchedRows = data as MatchedMemoryRow[] | null;
    if (!matchedRows || matchedRows.length === 0) return [];

    const ids = matchedRows.map((r) => r.id);

    // Fetch full memory rows for these matched IDs to populate all required fields
    const { data: fullMemories, error: selectError } = await supabase
        .from('memories')
        .select('*, parent_id, status, relationship_type')
        .in('id', ids);

    if (selectError) throw selectError;
    if (!fullMemories) return [];

    // Map matchedRows back with full records and include similarity
    const matchedMap = new Map<string, number>();
    for (const r of matchedRows) {
        matchedMap.set(r.id, r.similarity);
    }

    const results = fullMemories.map((m: Memory) => ({
        ...m,
        similarity: matchedMap.get(m.id) ?? 0,
    }));

    // Sort by similarity descending (order returned by match_memories)
    results.sort((a, b) => (b.similarity || 0) - (a.similarity || 0));

    return results as Memory[];
}
