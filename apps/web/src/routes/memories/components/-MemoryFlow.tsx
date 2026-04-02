import * as React from 'react'
import * as d3 from 'd3'
import type { Memory } from './-MemoriesList'

interface MemoryFlowProps {
    memories: Memory[]
    onSelect?: (id: string) => void
}

export function MemoryFlow({ memories, onSelect }: MemoryFlowProps) {
    const containerRef = React.useRef<HTMLDivElement>(null)
    const [hoveredNode, setHoveredNode] = React.useState<Memory | null>(null)

    React.useEffect(() => {
        if (!containerRef.current || memories.length === 0) return

        const width = containerRef.current.clientWidth
        const height = 800

        d3.select(containerRef.current).selectAll('*').remove()

        const svg = d3.select(containerRef.current)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .attr('style', 'max-width: 100%; height: auto; background-color: transparent;')

        const rootId = 'ROOT_DUMMY_NODE'
        const nodes = memories.map(m => ({ ...m }))

        const idSet = new Set(nodes.map(n => n.id))

        const stratifiedData = [
            { id: rootId, content: 'Root', created_at: '', metadata: {} } as any,
            ...nodes.map(n => ({
                ...n,
                parentId: (n.parent_id && idSet.has(n.parent_id)) ? n.parent_id : rootId
            }))
        ]

        let root
        try {
            root = d3.stratify<any>()
                .id(d => d.id)
                .parentId(d => d.parentId)
                (stratifiedData)
        } catch (e) {
            console.error("Stratify failed", e)
            return
        }

        const nodeWidth = 240
        const nodeHeight = 90
        const tree = d3.tree<any>()
            .nodeSize([nodeWidth + 50, nodeHeight + 70])

        root.sort((a, b) => (a.data.created_at || 0) < (b.data.created_at || 0) ? 1 : -1)

        tree(root)

        let x0 = Infinity;
        let x1 = -x0;
        let y0 = Infinity;
        let y1 = -y0;
        root.each(d => {
            const x = d.x ?? 0
            const y = d.y ?? 0
            if (x > x1) x1 = x;
            if (x < x0) x0 = x;
            if (y > y1) y1 = y;
            if (y < y0) y0 = y;
        });

        const treeHeight = y1 - y0 + nodeHeight + 100

        svg.attr("height", Math.max(height, treeHeight))

        const initialTranslateX = (width / 2) - ((x0 + x1) / 2)
        const initialTranslateY = 50

        const g = svg.append("g")
            .attr("transform", `translate(${initialTranslateX},${initialTranslateY})`);

        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.15, 3])
            .on('zoom', (event) => {
                g.attr('transform', event.transform)
            })

        svg.call(zoom)
            .call(zoom.transform, d3.zoomIdentity.translate(initialTranslateX, initialTranslateY).scale(0.75))
            .on("dblclick.zoom", null)

        // Gradient definitions
        const defs = svg.append('defs')
        
        // Link gradient
        const linkGradient = defs.append('linearGradient')
            .attr('id', 'link-gradient')
            .attr('gradientUnits', 'userSpaceOnUse')
            .attr('x1', 0).attr('y1', 0)
            .attr('x2', 0).attr('y2', height)
        
        linkGradient.append('stop')
            .attr('offset', '0%')
            .attr('stop-color', '#e5e7eb')
            .attr('stop-opacity', 0.3)
        
        linkGradient.append('stop')
            .attr('offset', '50%')
            .attr('stop-color', '#3b82f6')
            .attr('stop-opacity', 0.6)
        
        linkGradient.append('stop')
            .attr('offset', '100%')
            .attr('stop-color', '#e5e7eb')
            .attr('stop-opacity', 0.3)

        // Links with enhanced styling
        g.selectAll(".link")
            .data(root.links())
            .enter().append("path")
            .attr("class", "link")
            .attr("fill", "none")
            .attr("stroke", "url(#link-gradient)")
            .attr("stroke-width", 1.5)
            .attr("opacity", 0.6)
            .attr("d", d3.linkVertical()
                .x((d: any) => d.x || 0)
                .y((d: any) => d.y || 0) as any
            );

        // Nodes
        const node = g.selectAll(".node")
            .data(root.descendants().slice(1))
            .enter().append("g")
            .attr("class", d => `node ${d.children ? "node--internal" : "node--leaf"}`)
            .attr("transform", (d: any) => `translate(${d.x || 0},${d.y || 0})`)
            .on('click', (event, d) => {
                onSelect?.(d.data.id)
            })
            .on('mouseenter', (event, d) => {
                setHoveredNode(d.data)
                d3.select(event.currentTarget).select('rect').attr('stroke-width', 3)
            })
            .on('mouseleave', (event, d) => {
                setHoveredNode(null)
                const m = d.data as Memory
                let strokeColor = '#d4d4d8'
                if (m.status === 'RESOLVED') strokeColor = '#71717a'
                else if (m.relationship_type === 'UPDATE') strokeColor = '#3b82f6'
                else if (m.relationship_type === 'REVERSAL') strokeColor = '#ef4444'
                else if (m.relationship_type === 'RESOLUTION') strokeColor = '#10b981'
                d3.select(event.currentTarget).select('rect').attr('stroke-width', 2).attr('stroke', strokeColor)
            })

        // Node shadow filter
        defs.append('filter')
            .attr('id', 'node-shadow')
            .attr('x', '-50%')
            .attr('y', '-50%')
            .attr('width', '200%')
            .attr('height', '200%')
            .append('feDropShadow')
            .attr('dx', 0)
            .attr('dy', 4)
            .attr('stdDeviation', 8)
            .attr('flood-opacity', 0.15)

        // Node Rects with enhanced styling
        node.append("rect")
            .attr("width", nodeWidth)
            .attr("height", nodeHeight)
            .attr("rx", 12)
            .attr("x", -nodeWidth / 2)
            .attr("y", 0)
            .attr("fill", "white")
            .attr("stroke", d => {
                const m = d.data as Memory
                if (m.status === 'RESOLVED') return '#71717a'
                if (m.relationship_type === 'UPDATE') return '#3b82f6'
                if (m.relationship_type === 'REVERSAL') return '#ef4444'
                if (m.relationship_type === 'RESOLUTION') return '#10b981'
                return '#d4d4d8'
            })
            .attr("stroke-width", 2)
            .attr("filter", "url(#node-shadow)")
            .attr("class", "cursor-pointer transition-colors duration-200")

        // Node accent bar
        node.append("rect")
            .attr("width", nodeWidth - 24)
            .attr("height", 3)
            .attr("rx", 1.5)
            .attr("x", -nodeWidth / 2 + 12)
            .attr("y", 8)
            .attr("fill", d => {
                const m = d.data as Memory
                const type = m.metadata?.type
                if (type === 'consensus_event') return '#3b82f6'
                if (type === 'decision_reasoning') return '#a855f7'
                if (type === 'post_mortem') return '#eab308'
                return '#71717a'
            })

        // Text: Type
        node.append("text")
            .attr("dy", 28)
            .attr("x", -nodeWidth / 2 + 16)
            .attr("text-anchor", "start")
            .text((d: any) => {
                const t = d.data.metadata?.type?.replace('_', ' ') || 'Memory'
                return t.charAt(0).toUpperCase() + t.slice(1).replace('_', ' ')
            })
            .attr("class", "text-[9px] font-bold fill-zinc-500 pointer-events-none uppercase tracking-wider")

        // Text: Date
        node.append("text")
            .attr("dy", 28)
            .attr("x", nodeWidth / 2 - 16)
            .attr("text-anchor", "end")
            .text((d: any) => {
                if (!d.data.created_at) return ''
                return new Date(d.data.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
            })
            .attr("class", "text-[9px] font-medium fill-zinc-400 pointer-events-none")

        // Text: Content
        node.append("foreignObject")
            .attr("width", nodeWidth - 32)
            .attr("height", 52)
            .attr("x", -nodeWidth / 2 + 16)
            .attr("y", 36)
            .append("xhtml:div")
            .style("font-size", "11px")
            .style("line-height", "1.45")
            .style("color", "#18181b")
            .style("overflow", "hidden")
            .style("text-overflow", "ellipsis")
            .style("display", "-webkit-box")
            .style("-webkit-line-clamp", "2")
            .style("-webkit-box-orient", "vertical")
            .style("pointer-events", "none")
            .style("font-weight", "500")
            .html(d => d.data.content)

    }, [memories, onSelect])

    return (
        <div className="relative border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-gradient-to-br from-zinc-50 to-white dark:from-zinc-950 dark:to-zinc-900 overflow-hidden h-[800px] mb-8 shadow-inner">
            {/* Grid pattern overlay */}
            <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]" 
                 style={{ 
                     backgroundImage: 'linear-gradient(#3b82f6 1px, transparent 1px), linear-gradient(90deg, #3b82f6 1px, transparent 1px)', 
                     backgroundSize: '40px 40px' 
                 }} 
            />
            
            <div ref={containerRef} className="relative w-full h-full cursor-grab active:cursor-grabbing" />

            {/* Hover Tooltip */}
            {hoveredNode && (
                <div className="absolute top-4 right-4 p-5 bg-white dark:bg-zinc-900 shadow-2xl rounded-2xl border border-zinc-200 dark:border-zinc-800 max-w-sm pointer-events-none z-10 animate-in fade-in zoom-in-95 duration-150">
                    <div className="flex items-center gap-2 mb-2">
                        <div className={`w-2 h-2 rounded-full ${
                            hoveredNode.relationship_type === 'UPDATE' ? 'bg-electric-blue-500' :
                            hoveredNode.relationship_type === 'REVERSAL' ? 'bg-alert-red-500' :
                            hoveredNode.relationship_type === 'RESOLUTION' ? 'bg-neon-green-500' :
                            'bg-zinc-400'
                        }`} />
                        <div className="text-xs font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                            {hoveredNode.metadata?.type?.replace('_', ' ')}
                        </div>
                    </div>
                    <div className="text-sm font-medium text-zinc-800 dark:text-zinc-200 leading-relaxed mb-3">
                        {hoveredNode.content}
                    </div>
                    <div className="text-xs text-zinc-400 dark:text-zinc-500 border-t border-zinc-100 dark:border-zinc-800 pt-3 flex justify-between items-center">
                        <span>{new Date(hoveredNode.created_at).toLocaleString()}</span>
                        {hoveredNode.status && (
                            <span className="px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-[10px] font-bold uppercase">
                                {hoveredNode.status}
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Legend */}
            <div className="absolute bottom-4 left-4 flex flex-wrap gap-3 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-sm p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 z-10 shadow-lg">
                <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-electric-blue-500 shadow-sm shadow-electric-blue-500/50"></div>
                    <span className="text-[10px] font-semibold text-zinc-600 dark:text-zinc-400">Update</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50"></div>
                    <span className="text-[10px] font-semibold text-zinc-600 dark:text-zinc-400">Resolution</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-alert-red-500 shadow-sm shadow-alert-red-500/50"></div>
                    <span className="text-[10px] font-semibold text-zinc-600 dark:text-zinc-400">Reversal</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-zinc-500"></div>
                    <span className="text-[10px] font-semibold text-zinc-600 dark:text-zinc-400">Resolved</span>
                </div>
            </div>

            {/* Type Legend */}
            <div className="absolute top-4 left-4 flex flex-wrap gap-2 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-sm p-2.5 rounded-xl border border-zinc-200 dark:border-zinc-800 z-10 shadow-lg">
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-electric-blue-50 dark:bg-electric-blue-950/30 border border-electric-blue-100 dark:border-electric-blue-900">
                    <div className="w-2 h-2 rounded-sm bg-electric-blue-500"></div>
                    <span className="text-[9px] font-bold text-electric-blue-700 dark:text-electric-blue-300 uppercase">Event</span>
                </div>
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-deep-purple-50 dark:bg-deep-purple-950/30 border border-deep-purple-100 dark:border-deep-purple-900">
                    <div className="w-2 h-2 rounded-sm bg-deep-purple-500"></div>
                    <span className="text-[9px] font-bold text-deep-purple-700 dark:text-deep-purple-300 uppercase">Decision</span>
                </div>
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-cyber-yellow-50 dark:bg-cyber-yellow-950/30 border border-cyber-yellow-100 dark:border-cyber-yellow-900">
                    <div className="w-2 h-2 rounded-sm bg-cyber-yellow-500"></div>
                    <span className="text-[9px] font-bold text-cyber-yellow-700 dark:text-cyber-yellow-300 uppercase">Post-Mortem</span>
                </div>
            </div>

            {/* Instructions */}
            <div className="absolute top-4 right-4 text-[10px] text-zinc-400 dark:text-zinc-500 font-medium bg-white/90 dark:bg-zinc-900/90 backdrop-blur-sm px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-800 z-10 shadow-sm">
                <span className="hidden md:inline">Scroll to Zoom • Drag to Pan • Click to Navigate</span>
                <span className="md:hidden">Tap to Navigate</span>
            </div>
        </div>
    )
}
