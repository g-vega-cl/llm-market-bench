import * as d3 from 'd3';
import { useEffect, useRef } from 'react';
import type { SectorPrediction } from '../api/fetch-predictions';

interface ChartEntry {
    date: Date;
    dateStr: string;
    deepseek?: number;
    minimax?: number;
}

export function AIPredictionChart({ data }: { data: SectorPrediction[] }) {
    const svgRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        if (!data || data.length === 0 || !svgRef.current) return;

        const evaluated = data.filter(
            (d) => d.status === 'evaluated' && d.sector_percentile_score != null,
        );
        if (evaluated.length === 0) return;

        // Prepare data grouped by target date
        const dateMap = new Map<string, ChartEntry>();

        evaluated.forEach((item) => {
            const dateStr = new Date(item.target_date).toLocaleDateString();
            if (!dateMap.has(dateStr)) {
                dateMap.set(dateStr, { date: new Date(item.target_date), dateStr });
            }
            const entry = dateMap.get(dateStr);
            if (!entry) return;
            const score =
                ((item.sector_percentile_score || 0) + (item.pair_percentile_score || 0)) / 2;

            if (item.model_name.startsWith('deepseek')) {
                entry.deepseek = score;
            } else if (item.model_name === 'MiniMax-M3') {
                entry.minimax = score;
            }
        });

        const chartData = Array.from(dateMap.values()).sort(
            (a, b) => a.date.getTime() - b.date.getTime(),
        );

        // D3 Chart Setup
        const margin = { top: 20, right: 30, left: 40, bottom: 30 };
        const width = 800 - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;

        // Clear existing SVG
        d3.select(svgRef.current).selectAll('*').remove();

        const svg = d3
            .select(svgRef.current)
            .attr(
                'viewBox',
                `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`,
            )
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Scales
        const x = d3
            .scaleTime()
            .domain(d3.extent(chartData, (d) => d.date) as [Date, Date])
            .range([0, width]);

        const y = d3.scaleLinear().domain([0, 100]).range([height, 0]);

        // Grid lines
        const yAxisGrid = d3
            .axisLeft(y)
            .tickSize(-width)
            .tickFormat(() => '')
            .ticks(5);
        svg.append('g')
            .attr('class', 'grid')
            .call(yAxisGrid)
            .selectAll('line')
            .style('stroke', '#334155')
            .style('stroke-dasharray', '3 3');

        svg.select('.domain').remove();

        // Axes
        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x).ticks(5))
            .style('color', '#94a3b8')
            .style('font-size', '12px');

        svg.append('g')
            .call(d3.axisLeft(y).ticks(5))
            .style('color', '#94a3b8')
            .style('font-size', '12px');

        // Line generator
        const lineGenerator = (key: 'deepseek' | 'minimax') =>
            d3
                .line<ChartEntry>()
                .defined((d) => d[key] !== undefined)
                .x((d) => x(d.date))
                .y((d) => y(d[key] ?? 0));

        // DeepSeek Line
        svg.append('path')
            .datum(chartData)
            .attr('fill', 'none')
            .attr('stroke', '#60a5fa')
            .attr('stroke-width', 3)
            .attr('d', lineGenerator('deepseek'));

        // MiniMax Line
        svg.append('path')
            .datum(chartData)
            .attr('fill', 'none')
            .attr('stroke', '#34d399')
            .attr('stroke-width', 3)
            .attr('d', lineGenerator('minimax'));

        // Dots
        const addDots = (key: 'deepseek' | 'minimax', color: string) => {
            svg.selectAll(`.dot-${key}`)
                .data(chartData.filter((d) => d[key] !== undefined))
                .enter()
                .append('circle')
                .attr('class', `dot-${key}`)
                .attr('cx', (d) => x(d.date))
                .attr('cy', (d) => y(d[key] ?? 0))
                .attr('r', 4)
                .attr('fill', color)
                .attr('stroke', '#1e293b')
                .attr('stroke-width', 2);
        };

        addDots('deepseek', '#60a5fa');
        addDots('minimax', '#34d399');

        // Legend
        const legend = svg.append('g').attr('transform', `translate(${width - 150}, 0)`);

        legend.append('circle').attr('cx', 0).attr('cy', 0).attr('r', 5).style('fill', '#60a5fa');
        legend
            .append('text')
            .attr('x', 10)
            .attr('y', 4)
            .text('DeepSeek Flash')
            .style('fill', '#f8fafc')
            .style('font-size', '12px')
            .attr('alignment-baseline', 'middle');

        legend.append('circle').attr('cx', 0).attr('cy', 20).attr('r', 5).style('fill', '#34d399');
        legend
            .append('text')
            .attr('x', 10)
            .attr('y', 24)
            .text('MiniMax-M3')
            .style('fill', '#f8fafc')
            .style('font-size', '12px')
            .attr('alignment-baseline', 'middle');
    }, [data]);

    return (
        <div className="w-full overflow-hidden flex justify-center">
            <svg
                ref={svgRef}
                className="w-full max-w-[800px] h-auto"
                style={{ minHeight: '300px' }}
                role="img"
                aria-label="AI Prediction Chart"
            >
                <title>AI Prediction Chart</title>
            </svg>
        </div>
    );
}
