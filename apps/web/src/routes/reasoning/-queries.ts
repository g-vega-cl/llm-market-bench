import { getSupabaseBrowserClient } from '~/lib/supabase-client'

export interface FetchReasoningLogsOptions {
    limit?: number
    offset?: number
    taskType?: string
    startDate?: string
    isAllTime?: boolean
}

export async function fetchReasoningLogs({
    limit = 20,
    offset = 0,
    taskType = 'ALL',
    startDate,
    isAllTime = false
}: FetchReasoningLogsOptions = {}) {
    const supabase = getSupabaseBrowserClient()

    let query = supabase
        .from('llm_reasoning_logs')
        .select('*', { count: 'exact' })
        .order('created_at', { ascending: false })
        .range(offset, offset + limit - 1)

    if (taskType && taskType !== 'ALL') {
        query = query.eq('task_type', taskType)
    }

    if (startDate) {
        query = query.gte('created_at', startDate)
    } else if (!isAllTime) {
        // Default to last 7 days if no startDate is provided and isAllTime is false
        const sevenDaysAgo = new Date()
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
        query = query.gte('created_at', sevenDaysAgo.toISOString())
    }
    // If isAllTime is true and startDate is missing, we don't apply any date filter.

    const { data, error, count } = await query

    if (error) {
        console.error('Error fetching reasoning logs:', error)
        throw error
    }

    return {
        data: data || [],
        count: count || 0,
        hasMore: count ? offset + (data?.length || 0) < count : false
    }
}
