import { getSupabaseBrowserClient } from '~/lib/supabase-client'

export async function fetchReasoningLogs() {
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
