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
