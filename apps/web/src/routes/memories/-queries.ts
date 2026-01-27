import { getSupabaseBrowserClient } from '~/lib/supabase-client'

export async function fetchMemories() {
  const supabase = getSupabaseBrowserClient()
  const { data, error } = await supabase
    .from('memories')
    .select('*, parent_id, status, relationship_type')
    .order('created_at', { ascending: false })

  if (error) throw error
  return data
}
