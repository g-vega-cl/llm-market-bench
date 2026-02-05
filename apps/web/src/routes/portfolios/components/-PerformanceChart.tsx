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

  }, [data])

  return (
    <div className="w-full bg-white border border-zinc-200 rounded-xl p-4 shadow-sm overflow-hidden">
      <h3 className="text-sm font-medium text-zinc-500 mb-4 uppercase tracking-wider">Equity Curve</h3>
      <div className="w-full overflow-x-auto">
        <svg
          ref={svgRef}
          width="100%"
          height="400"
          viewBox="0 0 800 400"
          preserveAspectRatio="xMidYMid meet"
        />
      </div>
    </div>
  )
}
