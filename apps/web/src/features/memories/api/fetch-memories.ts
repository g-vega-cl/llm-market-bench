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
        case 'consensus_event':
            return query.eq('memory_type', 'MARKET_EVENT');
        case 'calendar_event':
            return query.eq('memory_type', 'CALENDAR_EVENT');
        case 'academic_paper':
            return query
                .eq('memory_type', 'LESSON_LEARNED')
                .eq('metadata->source_type', 'academic_paper');
        case 'post_mortem':
            return query.not('metadata->analysis_window', 'is', null);
        case 'lesson_learned':
            return query
                .eq('memory_type', 'LESSON_LEARNED')
                .is('metadata->analysis_window', null)
                .or('metadata->source_type.is.null,metadata->source_type.neq.academic_paper');
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
