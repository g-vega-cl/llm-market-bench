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
        const height = 800 // Start with a reasonable height

        // Clear previous
        d3.select(containerRef.current).selectAll('*').remove()

        const svg = d3.select(containerRef.current)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .attr('style', 'max-width: 100%; height: auto; background-color: #fafafa;')

        const rootId = 'ROOT_DUMMY_NODE'
        const nodes = memories.map(m => ({ ...m }))

        // Find valid parent connections
        const idSet = new Set(nodes.map(n => n.id))

        // Adjust data for stratify: Connect orphans to Dummy Root
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

        const nodeWidth = 220
        const nodeHeight = 80
        const tree = d3.tree<any>()
            .nodeSize([nodeWidth + 40, nodeHeight + 60]) // Spacing

        // Sort by date to make it deterministic
        root.sort((a, b) => (a.data.created_at || 0) < (b.data.created_at || 0) ? 1 : -1)

        tree(root)

        // Calculate bounds
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

        // Calculate required dimensions
        const treeHeight = y1 - y0 + nodeHeight + 100
        // const treeWidth = x1 - x0 + nodeWidth + 100

        // Auto-resize SVG to fit the tree vertically if it's huge
        // But since we zoom, maybe we just want a large area? 
        // Let's make it at least the tree height so it doesn't get clipped initially
        svg.attr("height", Math.max(height, treeHeight))

        // Initial Center calculation
        // Tree is centered around x=0 by d3.tree
        // We want to translate (0,0) of tree to (width/2, 40) of SVG
        // Actually d.x is the vertical coordinate in d3.tree default? 
        // Wait, d3.tree default is top-down. x is horizontal, y is vertical.
        // Yes.
        // Range of x is [x0, x1]. Center is (x0+x1)/2. 
        // We want to move (x0+x1)/2 to width/2.
        const initialTranslateX = (width / 2) - ((x0 + x1) / 2)
        const initialTranslateY = 40

        const g = svg.append("g")
            .attr("transform", `translate(${initialTranslateX},${initialTranslateY})`);

        // Zoom Behavior
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform)
            })

        svg.call(zoom)
            // Set initial transform
            .call(zoom.transform, d3.zoomIdentity.translate(initialTranslateX, initialTranslateY).scale(0.8)) // Start slightly zoomed out
            .on("dblclick.zoom", null) // Disable double click zoom

        // Links
        g.selectAll(".link")
            .data(root.links())
            .enter().append("path")
            .attr("class", "link")
            .attr("fill", "none")
            .attr("stroke", "#e5e7eb")
            .attr("stroke-width", 2)
            .attr("d", d3.linkVertical()
                .x((d: any) => d.x || 0)
                .y((d: any) => d.y || 0) as any
            );

        // Nodes
        const node = g.selectAll(".node")
            .data(root.descendants().slice(1)) // Skip dummy root
            .enter().append("g")
            .attr("class", d => `node ${d.children ? "node--internal" : "node--leaf"}`)
            .attr("transform", (d: any) => `translate(${d.x || 0},${d.y || 0})`)
            .on('click', (event, d) => {
                onSelect?.(d.data.id)
            })
            .on('mouseenter', (event, d) => {
                setHoveredNode(d.data)
            })
            .on('mouseleave', () => {
                setHoveredNode(null)
            })

        // Node Rects
        node.append("rect")
            .attr("width", nodeWidth)
            .attr("height", nodeHeight)
            .attr("rx", 8)
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
            .attr("class", "cursor-pointer hover:stroke-zinc-800 transition-colors shadow-sm")

        // Text: Type
        node.append("text")
            .attr("dy", 20)
            .attr("x", -nodeWidth / 2 + 12)
            .attr("text-anchor", "start")
            .text((d: any) => {
                const t = d.data.metadata?.type?.replace('_', ' ') || 'Memory'
                // return t.toUpperCase()
                // Make it nicer
                return t.charAt(0).toUpperCase() + t.slice(1).replace('_', ' ')
            })
            .attr("class", "text-[10px] font-bold fill-zinc-500 pointer-events-none uppercase tracking-wider")

        // Text: Date
        node.append("text")
            .attr("dy", 20)
            .attr("x", nodeWidth / 2 - 12)
            .attr("text-anchor", "end")
            .text((d: any) => {
                if (!d.data.created_at) return ''
                return new Date(d.data.created_at).toLocaleDateString()
            })
            .attr("class", "text-[10px] font-medium fill-zinc-400 pointer-events-none")

        // Text: Content
        node.append("foreignObject")
            .attr("width", nodeWidth - 24)
            .attr("height", 46)
            .attr("x", -nodeWidth / 2 + 12)
            .attr("y", 28)
            .append("xhtml:div")
            .style("font-size", "11px")
            .style("line-height", "1.4")
            .style("color", "#18181b")
            .style("overflow", "hidden")
            .style("text-overflow", "ellipsis")
            .style("display", "-webkit-box")
            .style("-webkit-line-clamp", "2")
            .style("-webkit-box-orient", "vertical")
            .style("pointer-events", "none")
            .html(d => d.data.content)

    }, [memories, onSelect])

    return (
        <div className="relative border border-zinc-200 rounded-xl bg-zinc-50 overflow-hidden h-[800px] mb-8 shadow-inner">
            <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

            {hoveredNode && (
                <div className="absolute top-4 right-4 p-4 bg-white shadow-xl rounded-lg border border-zinc-200 max-w-sm pointer-events-none z-10 animate-in fade-in zoom-in-95 duration-100">
                    <div className="text-xs font-bold text-zinc-500 mb-1 uppercase tracking-wider">{hoveredNode.metadata?.type?.replace('_', ' ')}</div>
                    <div className="text-sm font-medium text-zinc-800 leading-relaxed">{hoveredNode.content}</div>
                    <div className="text-xs text-zinc-400 mt-2 border-t border-zinc-100 pt-2 flex justify-between">
                        <span>{new Date(hoveredNode.created_at).toLocaleString()}</span>
                        {hoveredNode.status && <span className="font-mono">{hoveredNode.status}</span>}
                    </div>
                </div>
            )}

            <div className="absolute bottom-4 left-4 flex gap-3 text-[10px] bg-white/90 p-2.5 rounded-lg backdrop-blur-sm border border-zinc-200 z-10 shadow-sm">
                <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-blue-500"></div>Update</div>
                <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>Resolution</div>
                <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-red-500"></div>Reversal</div>
                <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-zinc-500"></div>Resolved</div>
            </div>

            <div className="absolute top-4 left-4 text-[10px] text-zinc-400 font-medium bg-zinc-100/50 px-2 py-1 rounded">
                Mouse Wheel to Zoom • Drag to Pan
            </div>
        </div>
    )
}
