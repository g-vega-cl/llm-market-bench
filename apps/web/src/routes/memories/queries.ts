import { getSupabaseBrowserClient } from '~/lib/supabase-client'

export async function fetchMemories() {
  const supabase = getSupabaseBrowserClient()
  const { data, error } = await supabase
    .from('memories')
    .select('*')
    .order('created_at', { ascending: false })

  if (error) throw error
  return data
}
