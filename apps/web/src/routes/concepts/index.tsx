import * as React from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getSupabaseServerClient } from '~/lib/supabase'
import { ConceptMap, type Concept } from '~/routes/concepts/components/-ConceptMap'

// --- Data Loading ---

const fetchConcepts = createServerFn({ method: 'GET' }).handler(
  async (): Promise<Concept[]> => {
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
  },
)

export const Route = createFileRoute('/concepts/')({
  component: ConceptsRoute,
  loader: () => fetchConcepts(),
})

function ConceptsRoute() {
  const data = Route.useLoaderData()

  return (
    <div className="stack gap-fluid-2xl">
      <header className="stack gap-fluid-xs">
        <h1 className="text-fluid-4xl font-black text-zinc-900 dark:text-white tracking-tighter">
          Concept Cluster Map
        </h1>
        <p className="text-zinc-500 text-fluid-lg max-w-2xl">
          Semantic visualization of market narratives. Position represents
          semantic similarity (PCA), color represents momentum velocity.
        </p>
      </header>

      <div className="card-vibrant p-fluid-s overflow-hidden bg-zinc-50 dark:bg-zinc-950">
        <ConceptMap data={data} />
      </div>

      <div className="grid-auto-fit mt-fluid-xl pt-fluid-xl border-t-2 border-zinc-100 dark:border-zinc-800">
        <div className="stack gap-fluid-xs">
          <h3 className="text-fluid-base font-black uppercase tracking-widest flex items-center gap-fluid-s">
            <span className="w-4 h-4 rounded-full bg-gradient-to-r from-blue-500 via-green-500 to-red-500" />
            Momentum Velocity
          </h3>
          <p className="text-sm text-zinc-500 font-medium leading-snug">
            Acceleration of mentions (Last 7 Days vs 30-Day Avg).
            <br />
            <span className="text-blue-500 font-bold italic">Cool</span> = Stable
            / <span className="text-happy-red font-bold italic">Hot</span> = Viral
          </p>
        </div>

        <div className="stack gap-fluid-xs">
          <h3 className="text-fluid-base font-black uppercase tracking-widest flex items-center gap-fluid-s">
            <span className="w-4 h-4 rounded-full bg-zinc-300 dark:bg-zinc-600" />
            Size: Volume
          </h3>
          <p className="text-sm text-zinc-500 font-medium leading-snug">
            Larger circles indicate a higher total citation count across all
            newsletters (90-day history).
          </p>
        </div>

        <div className="stack gap-fluid-xs">
          <h3 className="text-fluid-base font-black uppercase tracking-widest flex items-center gap-fluid-s">
            <span className="w-4 h-4 text-[10px] font-black border-2 border-zinc-300 dark:border-zinc-600 flex items-center justify-center rounded">
              XY
            </span>
            Semantic Position
          </h3>
          <p className="text-sm text-zinc-500 font-medium leading-snug">
            Concepts appearing close together share semantic meaning in the
            vector space.
          </p>
        </div>
      </div>
    </div>
  )
}

