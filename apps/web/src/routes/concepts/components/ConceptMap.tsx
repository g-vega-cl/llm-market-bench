import * as React from 'react'
import * as d3 from 'd3'

export type Concept = {
  id: string
  concept_name: string
  pca_x: number | null
  pca_y: number | null
  mention_count: number
  velocity_score: number
  first_mention_at: string
}

export function ConceptMap({ data }: { data: Concept[] }) {
  const svgRef = React.useRef<SVGSVGElement>(null)
  const [hoveredNode, setHoveredNode] = React.useState<Concept | null>(null)
  const [hoveredCluster, setHoveredCluster] = React.useState<{ text: string, x: number, y: number, color: string } | null>(null)

  // Debug Stats
  const conceptCount = data.length

  React.useEffect(() => {
    if (!data || data.length === 0 || !svgRef.current) return

    const width = 800
    const height = 600
    const margin = { top: 20, right: 20, bottom: 20, left: 20 }
    const centerX = width / 2
    const centerY = height / 2

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // Scales
    const xExtent = d3.extent(data, (d) => d.pca_x!) as [number, number]
    const yExtent = d3.extent(data, (d) => d.pca_y!) as [number, number]

    const xPad = (xExtent[1] - xExtent[0]) * 0.05
    const yPad = (yExtent[1] - yExtent[0]) * 0.05

    const xScale = d3
      .scaleLinear()
      .domain([xExtent[0] - xPad, xExtent[1] + xPad])
      .range([margin.left, width - margin.right])

    const yScale = d3
      .scaleLinear()
      .domain([yExtent[0] - yPad, yExtent[1] + yPad])
      .range([height - margin.bottom, margin.top])

    const rScale = d3
      .scaleSqrt()
      .domain([0, d3.max(data, (d) => d.mention_count) || 10])
      .range([3, 12])

    // --- Node Color Scale (Velocity - Restored) ---
    const velocityScale = d3
      .scaleSequential(d3.interpolateTurbo)
      .domain([0, d3.max(data, (d) => d.velocity_score) || 5])

    // --- Spatial Color Scale (Background Only) ---
    const getSpatialColor = (x: number, y: number) => {
      const dx = x - centerX
      const dy = y - centerY
      const angle = Math.atan2(dy, dx)
      const t = (angle + Math.PI) / (2 * Math.PI)
      return d3.interpolateRainbow(t)
    }

    // --- Contours ---
    // 1. Generate standard contours (MultiPolygons)
    const contoursRaw = d3.contourDensity<Concept>()
      .x((d) => xScale(d.pca_x!))
      .y((d) => yScale(d.pca_y!))
      .size([width, height])
      .bandwidth(20)
      .thresholds(20)
      (data)

    // 2. Split MultiPolygons into Individual Polygons (Islands)
    // This ensures that two distant clusters at the same density level are treated as separate hover targets.
    type ContourFeature = {
      type: "Feature",
      geometry: { type: "Polygon", coordinates: any[][][] },
      properties: { value: number } // Density value
    }

    const separateContours: ContourFeature[] = []

    contoursRaw.forEach(multiPoly => {
      // multiPoly.coordinates is [Polygon1, Polygon2, ...]
      // Where each Polygon is [Ring1, Ring2...]
      multiPoly.coordinates.forEach(polygonCoords => {
        separateContours.push({
          type: "Feature",
          geometry: {
            type: "Polygon",
            coordinates: polygonCoords
          },
          properties: { value: multiPoly.value }
        })
      })
    })

    const pathGenerator = d3.geoPath()

    // Draw Individual Contours
    svg.append("g")
      .attr("class", "contours")
      .selectAll("path")
      .data(separateContours)
      .enter().append("path")
      .attr("d", d => pathGenerator(d.geometry as any))
      .attr("fill", d => {
        const centroid = pathGenerator.centroid(d.geometry as any)
        if (!centroid || isNaN(centroid[0])) return "#eee"
        return getSpatialColor(centroid[0], centroid[1])
      })
      .attr("fill-opacity", d => 0.05 + (d.properties.value * 0.1))
      .attr("stroke", "white")
      .attr("stroke-width", 0.5)
      .attr("stroke-opacity", 0.1)
      .style("cursor", "crosshair")
      .on("mouseenter", function (event, d) {
        d3.select(this)
          .transition().duration(100)
          .attr("fill-opacity", 0.4)
          .attr("stroke-opacity", 0.8)

        const centroid = pathGenerator.centroid(d.geometry as any)
        if (centroid && !isNaN(centroid[0])) {
          const cx = centroid[0]
          const cy = centroid[1]

          // Find dominant concept for THIS specific island
          let closest: Concept | null = null
          let minDist = Infinity

          for (const c of data) {
            const dx = xScale(c.pca_x!) - cx
            const dy = yScale(c.pca_y!) - cy
            const dist = dx * dx + dy * dy
            if (dist < minDist) {
              minDist = dist
              closest = c
            }
          }

          if (closest) {
            setHoveredCluster({
              text: closest.concept_name,
              x: cx,
              y: cy,
              color: getSpatialColor(cx, cy)
            })
          }
        }
      })
      .on("mouseleave", function (event, d) {
        d3.select(this)
          .transition().duration(200)
          .attr("fill-opacity", 0.05 + (d.properties.value * 0.1))
          .attr("stroke-opacity", 0.1)
        setHoveredCluster(null)
      })


    // Draw Nodes (Restored Velocity Color)
    const pointsG = svg
      .append('g')
      .selectAll('circle')
      .data(data)
      .join('circle')
      .attr('cx', (d) => xScale(d.pca_x!))
      .attr('cy', (d) => yScale(d.pca_y!))
      .attr('r', (d) => rScale(d.mention_count))
      .attr('fill', (d) => velocityScale(d.velocity_score)) // Back to Velocity
      .attr('fill-opacity', 0.9)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1)
      .style('cursor', 'pointer')
      .on('mouseenter', (event, d) => {
        d3.select(event.currentTarget).raise()
        d3.select(event.currentTarget)
          .transition()
          .duration(150)
          .attr('r', rScale(d.mention_count) * 1.5)
          .attr('stroke-width', 2)
          .attr('stroke', '#000')
        setHoveredNode(d)
      })
      .on('mouseleave', (event, d) => {
        d3.select(event.currentTarget)
          .transition()
          .duration(150)
          .attr('r', rScale(d.mention_count))
          .attr('stroke', '#fff')
          .attr('stroke-width', 1)
        setHoveredNode(null)
      })

  }, [data])

  return (
    <div className="relative flex justify-center p-4">
      {/* Debug Info Overlay */}
      <div className="absolute top-6 left-6 z-10 text-[10px] text-gray-400 font-mono bg-white/50 p-1 rounded pointer-events-none">
        {conceptCount} items
      </div>

      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox="0 0 800 600"
        className="max-w-5xl border border-gray-200 rounded-xl bg-gray-50/30 shadow-sm"
      />

      {/* Region Label - Now uses the cluster's specific color */}
      {hoveredCluster && !hoveredNode && (
        <div
          className="absolute top-8 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-full border border-gray-200 shadow-sm pointer-events-none transition-all flex items-center gap-2 bg-white/95 backdrop-blur"
          style={{ borderLeft: `4px solid ${hoveredCluster.color}` }}
        >
          <span className="text-xs font-bold uppercase tracking-widest" style={{ color: hoveredCluster.color }}>Region</span>
          <span className="text-lg font-bold text-gray-800">{hoveredCluster.text}</span>
        </div>
      )}

      {hoveredNode && (
        <div className="absolute top-4 right-4 p-4 bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg shadow-lg max-w-xs pointer-events-none z-10">
          <h3 className="font-bold text-md mb-1 text-gray-800">{hoveredNode.concept_name}</h3>
          <div className="text-sm text-gray-600 space-y-1">
            <div className="flex justify-between">
              <span>Mentions:</span>
              <span className="font-mono">{hoveredNode.mention_count}</span>
            </div>
            <div className="flex justify-between">
              <span>Momentum:</span>
              <span className="font-mono" style={{ color: d3.interpolateTurbo(hoveredNode.velocity_score / 5) }}>
                {hoveredNode.velocity_score.toFixed(2)}
              </span>
            </div>
            <div className="text-xs text-gray-400 mt-2">
              First seen: {new Date(hoveredNode.first_mention_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
