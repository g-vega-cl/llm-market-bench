import * as React from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getSupabaseServerClient } from '~/lib/supabase'
import { ConceptMap, type Concept } from '~/components/ConceptMap'

// --- Data Loading ---

const fetchConcepts = createServerFn({ method: 'GET' }).handler(
  async (): Promise<Concept[]> => {
    const supabase = getSupabaseServerClient()
    const { data, error } = await supabase
      .from('concept_metrics')
      .select(
        'id, concept_name, pca_x, pca_y, mention_count, velocity_score, first_mention_at',
      )
      .not('pca_x', 'is', null)
      .limit(1000)

    if (error) {
      console.error('Error fetching concepts:', error)
      return []
    }
    return data as Concept[]
  },
)

export const Route = createFileRoute('/concepts/')({
  component: ConceptsRoute,
  loader: () => fetchConcepts(),
})

function ConceptsRoute() {
  const data = Route.useLoaderData()

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">
          Concept Cluster Map
        </h1>
        <p className="text-gray-500 text-lg">
          Semantic visualization of market narratives. Position represents
          semantic similarity (PCA), color represents momentum velocity.
        </p>
      </div>

      <ConceptMap data={data} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8  border-t border-gray-100 pt-8">
        <div>
          <h3 className="font-semibold mb-2 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 via-green-500 to-red-500" />
            Color: Momentum Velocity
          </h3>
          <p className="text-sm text-gray-500">
            Represents the acceleration of mentions (Last 7 Days vs 30-Day Avg).
            <br />
            <span className="text-blue-600 font-medium">Cool Colors</span> = Stable/Fading
            <br />
            <span className="text-red-600 font-medium">Hot Colors</span> = Emerging/Viral
          </p>
        </div>

        <div>
          <h3 className="font-semibold mb-2 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-gray-400" />
            Size: Volume
          </h3>
          <p className="text-sm text-gray-500">
            Larger circles indicate a higher total citation count across all newsletters (90-day history).
          </p>
        </div>

        <div>
          <h3 className="font-semibold mb-2 flex items-center gap-2">
            <span className="w-4 h-4 text-xs border border-gray-300 flex items-center justify-center rounded">XY</span>
            Position: Semantic Similarity
          </h3>
          <p className="text-sm text-gray-500">
            Concepts appearing close together share semantic meaning in the vector space (reduced from 768 dimensions via PCA).
          </p>
        </div>
      </div>
    </div>
  )
}

