import * as React from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getSupabaseServerClient } from '~/lib/supabase'
import * as d3 from 'd3'

// --- Data Loading ---
type Concept = {
  id: string
  concept_name: string
  pca_x: number | null
  pca_y: number | null
  mention_count: number
  velocity_score: number
  first_mention_at: string
}

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

// --- D3 Component ---
function ConceptMap({ data }: { data: Concept[] }) {
  const svgRef = React.useRef<SVGSVGElement>(null)
  const [hovered, setHovered] = React.useState<Concept | null>(null)

  React.useEffect(() => {
    if (!data || data.length === 0 || !svgRef.current) return

    const width = 800
    const height = 600
    const margin = { top: 20, right: 20, bottom: 20, left: 20 }

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove() // Clear previous

    // Scales
    const xExtent = d3.extent(data, (d) => d.pca_x!) as [number, number]
    const yExtent = d3.extent(data, (d) => d.pca_y!) as [number, number]

    const xScale = d3
      .scaleLinear()
      .domain(xExtent)
      .range([margin.left, width - margin.right])
      .nice()

    const yScale = d3
      .scaleLinear()
      .domain(yExtent)
      .range([height - margin.bottom, margin.top])
      .nice()

    const rScale = d3
      .scaleSqrt()
      .domain([0, d3.max(data, (d) => d.mention_count) || 10])
      .range([3, 10])

    const colorScale = d3
      .scaleSequential(d3.interpolateTurbo)
      .domain([0, d3.max(data, (d) => d.velocity_score) || 5])

    // Draw Points
    svg
      .append('g')
      .selectAll('circle')
      .data(data)
      .join('circle')
      .attr('cx', (d) => xScale(d.pca_x!))
      .attr('cy', (d) => yScale(d.pca_y!))
      .attr('r', 0) // Start at 0 for animation
      .attr('fill', (d) => colorScale(d.velocity_score))
      .attr('fill-opacity', 0.8)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1)
      .style('cursor', 'pointer')
      .on('mouseenter', (event, d) => {
        d3.select(event.currentTarget)
          .transition()
          .duration(200)
          .attr('r', rScale(d.mention_count) * 1.5)
          .attr('stroke-width', 2)
          .attr('stroke', '#000')
        setHovered(d)
      })
      .on('mouseleave', (event, d) => {
        d3.select(event.currentTarget)
          .transition()
          .duration(200)
          .attr('r', rScale(d.mention_count))
          .attr('stroke', '#fff')
          .attr('stroke-width', 1)
        setHovered(null)
      })
      .transition()
      .duration(1000)
      .delay((d, i) => i * 5) // Staggered entrance
      .attr('r', (d) => rScale(d.mention_count))

    // Optional: Add axes for reference? Maybe not needed for semantic map.
    // Making it look more like a "map" than a chart.
  }, [data])

  return (
    <div className="relative flex justify-center p-4">
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox="0 0 800 600"
        className="max-w-4xl border border-gray-200 rounded-xl bg-white shadow-sm"
      />
      {hovered && (
        <div className="absolute top-4 right-4 p-4 bg-white/90 backdrop-blur border border-gray-200 rounded-lg shadow-lg max-w-xs pointer-events-none">
          <h3 className="font-bold text-lg mb-1">{hovered.concept_name}</h3>
          <div className="text-sm text-gray-600 space-y-1">
            <div className="flex justify-between">
              <span>Mentions:</span>
              <span className="font-mono">{hovered.mention_count}</span>
            </div>
            <div className="flex justify-between">
              <span>Velocity:</span>
              <span
                className="font-mono"
                style={{
                  color: d3.interpolateTurbo(
                    hovered.velocity_score /
                      (d3.max(data, (d) => d.velocity_score) || 1),
                  ),
                }}
              >
                {hovered.velocity_score.toFixed(2)}x
              </span>
            </div>
            <div className="text-xs text-gray-400 mt-2">
              First seen: {new Date(hovered.first_mention_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 max-w-4xl border-t border-gray-100 pt-8">
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
