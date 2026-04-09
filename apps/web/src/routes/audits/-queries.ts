import { getSupabaseBrowserClient } from '~/lib/supabase-client'

export async function fetchAudits() {
  const supabase = getSupabaseBrowserClient()
  const { data, error } = await supabase
    .from('system_audits')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(100)

  if (error) throw error
  return data
}