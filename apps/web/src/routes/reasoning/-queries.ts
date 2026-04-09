import { getSupabaseBrowserClient } from '~/lib/supabase-client'
import type { LLMReasoningLog } from '@llm-market-bench/database'

const PAGE_SIZE = 50

export interface PaginatedReasoningLogs {
    data: LLMReasoningLog[]
    hasMore: boolean
    nextCursor: string | null
}

export async function fetchReasoningLogs(cursor?: string, pageSize: number = PAGE_SIZE): Promise<PaginatedReasoningLogs> {
    const supabase = getSupabaseBrowserClient()
    
    let query = supabase
        .from('llm_reasoning_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(pageSize + 1)

    if (cursor) {
        query = query.lt('created_at', cursor)
    }

    const { data, error } = await query

    if (error) {
        console.error('Error fetching reasoning logs:', error)
        throw error
    }

    const hasMore = data.length > pageSize
    const paginatedData = hasMore ? data.slice(0, pageSize) : data

    const nextCursor = hasMore && paginatedData.length > 0
        ? paginatedData[paginatedData.length - 1].created_at
        : null

    return {
        data: paginatedData,
        hasMore,
        nextCursor
    }
}

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
