import { getSupabaseBrowserClient } from '~/lib/supabase-client'

const PAGE_SIZE = 50

export interface ReasoningLog {
    id: string
    task_type: string
    model_provider: string
    model_name: string
    prompt: any[]
    response: any
    metadata: any
    created_at: string
}

export interface PaginatedReasoningLogs {
    data: ReasoningLog[]
    hasMore: boolean
    nextCursor: string | null
}

/**
 * Fetch reasoning logs with cursor-based pagination
 * @param cursor - The created_at timestamp of the last item from previous page
 * @param pageSize - Number of items per page (default: 50)
 */
export async function fetchReasoningLogs(cursor?: string, pageSize: number = PAGE_SIZE): Promise<PaginatedReasoningLogs> {
    const supabase = getSupabaseBrowserClient()
    
    let query = supabase
        .from('llm_reasoning_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(pageSize + 1) // Fetch one extra to check if there's more

    if (cursor) {
        query = query.lt('created_at', cursor)
    }

    const { data, error } = await query

    if (error) {
        console.error('Error fetching reasoning logs:', error)
        throw error
    }

    // Check if we have more data
    const hasMore = data.length > pageSize
    const paginatedData = hasMore ? data.slice(0, pageSize) : data

    // Get the cursor for the next page
    const nextCursor = hasMore && paginatedData.length > 0
        ? paginatedData[paginatedData.length - 1].created_at
        : null

    return {
        data: paginatedData,
        hasMore,
        nextCursor
    }
}

/**
 * Fetch all reasoning logs (legacy - use only for small datasets)
 * @deprecated Use fetchReasoningLogs with pagination instead
 */
export async function fetchAllReasoningLogs() {
    const supabase = getSupabaseBrowserClient()
    const { data, error } = await supabase
        .from('llm_reasoning_logs')
        .select('*')
        .order('created_at', { ascending: false })

    if (error) {
        console.error('Error fetching reasoning logs:', error)
        throw error
    }
    return data
}
