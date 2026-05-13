import { getSupabaseBrowserClient } from '~/lib/supabase-client';

const PAGE_SIZE = 50;

export interface SystemAudit {
    id: string;
    title: string;
    description: string;
    severity: string;
    audit_type: string;
    suggestion: string | null;
    created_at: string | null;
    metadata: any;
}

export interface PaginatedAudits {
    data: SystemAudit[];
    hasMore: boolean;
    nextCursor: string | null;
}

export async function fetchAudits(
    cursor?: string,
    pageSize: number = PAGE_SIZE,
): Promise<PaginatedAudits> {
    const supabase = getSupabaseBrowserClient();

    let query = supabase
        .from('system_audits')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(pageSize + 1);

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
