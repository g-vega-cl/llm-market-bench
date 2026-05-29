import * as d3 from 'd3';
import * as React from 'react';
import type { Memory } from './MemoriesList';

interface MemoryFlowProps {
    memories: Memory[];
    onSelect?: (id: string) => void;
}

interface StratifyData extends Memory {
    parentId: string | null;
}

export function MemoryFlow({ memories, onSelect }: MemoryFlowProps) {
    const containerRef = React.useRef<HTMLDivElement>(null);
    const [hoveredNode, setHoveredNode] = React.useState<Memory | null>(null);

    React.useEffect(() => {
        if (!containerRef.current || memories.length === 0) return;

        const width = containerRef.current.clientWidth;
        const height = 600;

        d3.select(containerRef.current).selectAll('*').remove();

        const svg = d3
            .select(containerRef.current)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .attr('style', 'max-width: 100%; height: auto; background-color: transparent;');

        const rootId = 'ROOT_DUMMY_NODE';
        const nodes = memories.map((m) => ({ ...m }));

        const idSet = new Set(nodes.map((n) => n.id));

        const stratifiedData: StratifyData[] = [
            {
                id: rootId,
                content: 'Root',
                created_at: '',
                metadata: {},
                parentId: null,
                status: null,
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: null,
                importance_score: null,
                target_date: null,
            },
            ...nodes.map((n) => ({
                ...n,
                parentId: n.parent_id && idSet.has(n.parent_id) ? n.parent_id : rootId,
            })),
        ];

        let root: d3.HierarchyNode<StratifyData>;
        try {
            root = d3
                .stratify<StratifyData>()
                .id((d) => d.id)
                .parentId((d) => d.parentId)(stratifiedData);
        } catch (e) {
            console.error('Stratify failed', e);
            return;
        }

        const nodeWidth = 220;
        const nodeHeight = 80;
        const tree = d3.tree<StratifyData>().nodeSize([nodeWidth + 40, nodeHeight + 50]);

        root.sort((a, b) => ((a.data.created_at || '') < (b.data.created_at || '') ? 1 : -1));

        tree(root);

        let x0 = Infinity;
        let x1 = -x0;
        let y0 = Infinity;
        let y1 = -y0;
        root.each((d) => {
            const x = d.x ?? 0;
            const y = d.y ?? 0;
            if (x > x1) x1 = x;
            if (x < x0) x0 = x;
            if (y > y1) y1 = y;
            if (y < y0) y0 = y;
        });

        const treeHeight = y1 - y0 + nodeHeight + 80;

        svg.attr('height', Math.max(height, treeHeight));

        const initialTranslateX = width / 2 - (x0 + x1) / 2;
        const initialTranslateY = 40;

        const g = svg
            .append('g')
            .attr('transform', `translate(${initialTranslateX},${initialTranslateY})`);

        const zoom = d3
            .zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.2, 2])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom)
            .call(
                zoom.transform,
                d3.zoomIdentity.translate(initialTranslateX, initialTranslateY).scale(0.7),
            )
            .on('dblclick.zoom', null);

        // Links
        const linkGenerator = d3
            .linkVertical<d3.HierarchyLink<StratifyData>, d3.HierarchyNode<StratifyData>>()
            .x((d) => d.x || 0)
            .y((d) => d.y || 0);

        g.selectAll('.link')
            .data(root.links())
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('fill', 'none')
            .attr('stroke', '#e4e4e7')
            .attr('stroke-width', 1)
            // biome-ignore lint/suspicious/noExplicitAny: D3 type casting
            .attr('d', linkGenerator as any);

        // Nodes
        const node = g
            .selectAll('.node')
            .data(root.descendants().slice(1))
            .enter()
            .append('g')
            .attr('class', (d) => `node ${d.children ? 'node--internal' : 'node--leaf'}`)
            .attr('transform', (d) => `translate(${d.x || 0},${d.y || 0})`)
            .on('click', (_event, d) => {
                onSelect?.(d.data.id);
            })
            .on('mouseenter', (event, d) => {
                setHoveredNode(d.data);
                d3.select(event.currentTarget).select('rect').attr('stroke-width', 2);
            })
            .on('mouseleave', (event, _d) => {
                setHoveredNode(null);
                d3.select(event.currentTarget).select('rect').attr('stroke-width', 1);
            });

        // Node Rects
        node.append('rect')
            .attr('width', nodeWidth)
            .attr('height', nodeHeight)
            .attr('rx', 4)
            .attr('x', -nodeWidth / 2)
            .attr('y', 0)
            .attr('fill', 'white')
            .attr('stroke', (d) => {
                const m = d.data as Memory;
                if (m.status === 'RESOLVED') return '#71717a';
                if (m.relationship_type === 'UPDATE') return '#3b82f6';
                if (m.relationship_type === 'REVERSAL') return '#ef4444';
                if (m.relationship_type === 'RESOLUTION') return '#16a34a';
                return '#d4d4d8';
            })
            .attr('stroke-width', 1)
            .attr('class', 'cursor-pointer');

        // Text: Type
        node.append('text')
            .attr('dy', 20)
            .attr('x', -nodeWidth / 2 + 12)
            .attr('text-anchor', 'start')
            .text((d) => {
                const t = d.data.metadata?.type?.replace('_', ' ') || 'Memory';
                return t.charAt(0).toUpperCase() + t.slice(1).replace('_', ' ');
            })
            .attr(
                'class',
                'text-[10px] font-medium fill-zinc-500 pointer-events-none uppercase tracking-wide',
            );

        // Text: Date
        node.append('text')
            .attr('dy', 20)
            .attr('x', nodeWidth / 2 - 12)
            .attr('text-anchor', 'end')
            .text((d) => {
                if (!d.data.created_at) return '';
                return new Date(d.data.created_at).toLocaleDateString('en-US', {
                    timeZone: 'America/New_York',
                });
            })
            .attr('class', 'text-[10px] font-mono fill-zinc-400 pointer-events-none');

        // Text: Content
        node.append('foreignObject')
            .attr('width', nodeWidth - 24)
            .attr('height', 46)
            .attr('x', -nodeWidth / 2 + 12)
            .attr('y', 28)
            .append('xhtml:div')
            .style('font-size', '11px')
            .style('line-height', '1.4')
            .style('color', '#3f3f46')
            .style('overflow', 'hidden')
            .style('text-overflow', 'ellipsis')
            .style('display', '-webkit-box')
            .style('-webkit-line-clamp', '2')
            .style('-webkit-box-orient', 'vertical')
            .style('pointer-events', 'none')
            .html((d) => d.data.content);
    }, [memories, onSelect]);

    return (
        <div className="relative border border-zinc-200 dark:border-zinc-800 rounded-md bg-white dark:bg-zinc-900 overflow-hidden h-[600px] mb-6">
            <div
                ref={containerRef}
                className="relative w-full h-full cursor-grab active:cursor-grabbing"
            />

            {/* Hover Tooltip */}
            {hoveredNode && (
                <div className="absolute top-4 right-4 p-4 bg-white dark:bg-zinc-900 shadow-lg rounded-md border border-zinc-200 dark:border-zinc-800 max-w-sm pointer-events-none z-10">
                    <div className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">
                        {hoveredNode.metadata?.type?.replace('_', ' ')}
                    </div>
                    <div className="text-sm text-zinc-800 dark:text-zinc-200 leading-relaxed mb-3">
                        {hoveredNode.content}
                    </div>
                    <div className="text-xs text-zinc-400 border-t border-zinc-200 dark:border-zinc-800 pt-2">
                        {hoveredNode.created_at
                            ? new Date(hoveredNode.created_at).toLocaleString()
                            : '-'}
                    </div>
                </div>
            )}

            {/* Legend */}
            <div className="absolute bottom-4 left-4 flex flex-wrap gap-4 bg-white/95 dark:bg-zinc-900/95 p-3 rounded border border-zinc-200 dark:border-zinc-800 z-10">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                    <span className="text-xs text-zinc-600 dark:text-zinc-400">Update</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                    <span className="text-xs text-zinc-600 dark:text-zinc-400">Resolution</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-rose-500"></div>
                    <span className="text-xs text-zinc-600 dark:text-zinc-400">Reversal</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-zinc-400"></div>
                    <span className="text-xs text-zinc-600 dark:text-zinc-400">Resolved</span>
                </div>
            </div>

            <div className="absolute top-4 right-4 text-xs text-zinc-400 bg-white/95 dark:bg-zinc-900/95 px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 z-10">
                Scroll to zoom • Drag to pan
            </div>
        </div>
    );
}
