import { getSupabaseServerClient } from '~/lib/supabase'
import type { Concept } from '../components/ConceptMap'

export { type Concept }

export async function fetchConcepts(): Promise<Concept[]> {
  const supabase = getSupabaseServerClient()
  const { data, error } = await supabase
    .from('concept_metrics')
    .select(
      'id, concept_name, pca_x, pca_y, mention_count, velocity_score, first_mention_at, last_mention_at',
    )
    .not('pca_x', 'is', null)
    .limit(1000)

  if (error) {
    console.error('Error fetching concepts:', error)
    return []
  }
  return data as Concept[]
}
