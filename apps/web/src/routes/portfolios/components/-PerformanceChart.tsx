import * as React from 'react'
import * as d3 from 'd3'

export type PerformanceSnapshot = {
  date: string
  total_equity: number
}

interface PerformanceChartProps {
  data: PerformanceSnapshot[]
}

export function PerformanceChart({ data }: PerformanceChartProps) {
  const svgRef = React.useRef<SVGSVGElement>(null)
  const [tooltipData, setTooltipData] = React.useState<{ date: string; equity: number; x: number; y: number } | null>(null)

  React.useEffect(() => {
    if (!data || data.length === 0 || !svgRef.current) return

    const margin = { top: 20, right: 30, bottom: 30, left: 60 }
    const width = 800 - margin.left - margin.right
    const height = 400 - margin.top - margin.bottom

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const parsedData = data.map(d => ({
      date: new Date(d.date),
      value: Number(d.total_equity)
    }))

    const x = d3.scaleTime()
      .domain(d3.extent(parsedData, d => d.date) as [Date, Date])
      .range([0, width])

    const y = d3.scaleLinear()
      .domain([
        d3.min(parsedData, d => d.value) || 0,
        d3.max(parsedData, d => d.value) || 10000
      ])
      .nice()
      .range([height, 0])

    const line = d3.line<{ date: Date; value: number }>()
      .x(d => x(d.date))
      .y(d => y(d.value))
      .curve(d3.curveMonotoneX)

    // Add X axis
    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(5))
      .attr('color', '#94a3b8') // zinc-400

    // Add Y axis
    g.append('g')
      .call(d3.axisLeft(y).tickFormat(d => `$${Number(d).toLocaleString()}`))
      .attr('color', '#94a3b8')

    // Add Gridlines
    g.append('g')
      .attr('class', 'grid')
      .attr('opacity', 0.1)
      .call(d3.axisLeft(y).tickSize(-width).tickFormat(() => ''))

    // Add the line
    g.append('path')
      .datum(parsedData)
      .attr('fill', 'none')
      .attr('stroke', '#0ea5e9') // sky-500
      .attr('stroke-width', 2)
      .attr('d', line)

    // Add Area under the line
    const area = d3.area<{ date: Date; value: number }>()
      .x(d => x(d.date))
      .y0(height)
      .y1(d => y(d.value))
      .curve(d3.curveMonotoneX)

    g.append('path')
      .datum(parsedData)
      .attr('fill', 'url(#line-gradient)')
      .attr('d', area)

    // Define gradient
    const gradient = svg.append('defs')
      .append('linearGradient')
      .attr('id', 'line-gradient')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%')

    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#0ea5e9')
      .attr('stop-opacity', 0.2)

    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#0ea5e9')
      .attr('stop-opacity', 0)

    // Create bisector for finding closest data point
    const bisector = d3.bisector<{ date: Date; value: number }, Date>(d => d.date).left

    // Add invisible overlay for mouse interaction
    const overlay = g.append('rect')
      .attr('class', 'overlay')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'none')
      .attr('pointer-events', 'all')
      .on('mousemove', function(event) {
        const [mouseX] = d3.pointer(event)
        const x0 = bisector(parsedData, x.invert(mouseX), 1)
        const d0 = parsedData[x0 - 1]
        const d1 = parsedData[x0]
        const d = d0 && d1 ? (mouseX - x(d0.date) < x(d1.date) - mouseX ? d0 : d1) : d0 || d1

        if (d) {
          setTooltipData({
            date: d.date.toLocaleDateString('en-US', { 
              year: 'numeric', 
              month: 'short', 
              day: 'numeric' 
            }),
            equity: d.value,
            x: x(d.date),
            y: y(d.value)
          })
        }
      })
      .on('mouseleave', function() {
        setTooltipData(null)
      })

    // Add vertical line (crosshair)
    const crosshair = g.append('line')
      .attr('class', 'crosshair')
      .attr('stroke', '#64748b')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4')
      .attr('opacity', 0)
      .attr('x1', 0)
      .attr('x2', 0)
      .attr('y1', 0)
      .attr('y2', height)

    // Add dot marker
    const dot = g.append('circle')
      .attr('class', 'dot')
      .attr('r', 6)
      .attr('fill', '#0ea5e9')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .attr('opacity', 0)

  }, [data])

  // Update crosshair and dot position when tooltipData changes
  React.useEffect(() => {
    if (!svgRef.current || !tooltipData) return
    
    const svg = d3.select(svgRef.current)
    if (svg.empty()) {
      return
    }

    svg.select('.crosshair')
      .attr('opacity', 1)
      .attr('transform', `translate(${tooltipData.x},0)`)

    svg.select('.dot')
      .attr('opacity', 1)
      .attr('cx', tooltipData.x)
      .attr('cy', tooltipData.y)
  }, [tooltipData])

  return (
    <div className="w-full bg-white border border-zinc-200 rounded-xl p-4 shadow-sm overflow-hidden">
      <h3 className="text-sm font-medium text-zinc-500 mb-4 uppercase tracking-wider">Equity Curve</h3>
      <div className="w-full overflow-x-auto relative">
        <svg
          ref={svgRef}
          width="100%"
          height="400"
          viewBox="0 0 800 400"
          preserveAspectRatio="xMidYMid meet"
        />
        {tooltipData && (
          <div
            className="absolute bg-zinc-900 text-white px-3 py-2 rounded-lg shadow-lg pointer-events-none z-10 text-sm"
            style={{
              left: Math.min(tooltipData.x + 10, 700),
              top: Math.max(tooltipData.y - 60, 10),
            }}
          >
            <div className="font-medium text-zinc-300 mb-1">{tooltipData.date}</div>
            <div className="font-bold text-lg">
              ${tooltipData.equity.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
