import type { LLMReasoningLog } from '@llm-market-bench/database';
import { getSupabaseBrowserClient } from '~/lib/supabase-client';

const PAGE_SIZE = 50;

export interface PaginatedReasoningLogs {
    data: LLMReasoningLog[];
    hasMore: boolean;
    nextCursor: string | null;
}

const ARCHIVE_DB_URL =
    process.env.NEXT_PUBLIC_ARCHIVE_DB_URL || 'https://benchify-archive-db.clvg.uk';

async function fetchFromArchive(
    cursor?: string | null,
    limit: number = PAGE_SIZE + 1,
): Promise<LLMReasoningLog[]> {
    try {
        const url = new URL(`${ARCHIVE_DB_URL}/llm_reasoning_logs`);
        url.searchParams.set('order', 'created_at.desc');
        url.searchParams.set('limit', String(limit));
        if (cursor) {
            url.searchParams.set('created_at', `lt.${cursor}`);
        }

        const res = await fetch(url.toString(), {
            headers: {
                Accept: 'application/json',
            },
            signal: AbortSignal.timeout(5000),
        });

        if (!res.ok) {
            return [];
        }

        const json = await res.json();
        return Array.isArray(json) ? (json as LLMReasoningLog[]) : [];
    } catch {
        return [];
    }
}

export async function fetchReasoningLogs(
    cursor?: string,
    pageSize: number = PAGE_SIZE,
): Promise<PaginatedReasoningLogs> {
    const supabase = getSupabaseBrowserClient();

    let query = supabase
        .from('llm_reasoning_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(pageSize + 1);

    if (cursor) {
        query = query.lt('created_at', cursor);
    }

    const { data: supabaseData, error } = await query;

    if (error) {
        console.error('Error fetching reasoning logs:', error);
        throw error;
    }

    let combinedData: LLMReasoningLog[] = (supabaseData || []) as LLMReasoningLog[];

    // If Supabase has fewer than requested (or none because cursor is older than hot retention),
    // seamlessly query the archive database
    if (combinedData.length < pageSize + 1) {
        const remainingNeeded = pageSize + 1 - combinedData.length;
        const archiveCursor =
            combinedData.length > 0 ? combinedData[combinedData.length - 1].created_at : cursor;

        const archiveLogs = await fetchFromArchive(archiveCursor, remainingNeeded);
        if (archiveLogs.length > 0) {
            combinedData = [...combinedData, ...archiveLogs];
        }
    }

    const hasMore = combinedData.length > pageSize;
    const paginatedData = hasMore ? combinedData.slice(0, pageSize) : combinedData;

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

export async function fetchAllReasoningLogs(): Promise<LLMReasoningLog[]> {
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase
        .from('llm_reasoning_logs')
        .select('*')
        .order('created_at', { ascending: false });

    if (error) {
        console.error('Error fetching reasoning logs:', error);
        throw error;
    }

    const archiveLogs = await fetchFromArchive(undefined, 10000);
    return [...(data || []), ...archiveLogs] as LLMReasoningLog[];
}
