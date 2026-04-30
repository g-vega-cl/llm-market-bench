import { getSupabaseBrowserClient } from '~/lib/supabase-client'

export async function fetchCauseAndEffect() {
  const supabase = getSupabaseBrowserClient()
  const { data, error } = await supabase
    .from('cause_and_effect')
    .select('*, event:memories(*)')
    .order('created_at', { ascending: false })

  if (error) throw error
  return data
}
