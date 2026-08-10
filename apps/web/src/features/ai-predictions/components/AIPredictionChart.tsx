import * as d3 from 'd3';
import { useEffect, useRef } from 'react';
import type { SectorPrediction } from '../api/fetch-predictions';

interface ChartEntry {
    date: Date;
    dateStr: string;
    deepseek?: number;
    minimax?: number;
    gemini?: number;
    openai?: number;
    deepseekSum?: number;
    deepseekCount?: number;
    minimaxSum?: number;
    minimaxCount?: number;
    geminiSum?: number;
    geminiCount?: number;
    openaiSum?: number;
    openaiCount?: number;
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

        const getOrCreateEntry = (dateStr: string, date: string): ChartEntry => {
            let entry = dateMap.get(dateStr);
            if (!entry) {
                entry = {
                    date: new Date(date),
                    dateStr,
                    deepseekSum: 0,
                    deepseekCount: 0,
                    minimaxSum: 0,
                    minimaxCount: 0,
                    geminiSum: 0,
                    geminiCount: 0,
                    openaiSum: 0,
                    openaiCount: 0,
                };
                dateMap.set(dateStr, entry);
            }
            return entry;
        };

        function getModelKey(modelName: string): ModelKey | null {
            const lower = modelName.toLowerCase();
            if (lower.includes('deepseek')) return 'deepseek';
            if (lower.includes('minimax')) return 'minimax';
            if (lower.includes('gemini')) return 'gemini';
            if (lower.includes('gpt') || lower.includes('openai')) return 'openai';
            return null;
        }

        function updateEntryScore(entry: ChartEntry, modelName: string, score: number) {
            const key = getModelKey(modelName);
            if (!key) return;
            const sumKey = `${key}Sum` as keyof ChartEntry;
            const countKey = `${key}Count` as keyof ChartEntry;
            (entry as unknown as Record<string, unknown>)[sumKey] =
                ((entry[sumKey] as number | undefined) ?? 0) + score;
            (entry as unknown as Record<string, unknown>)[countKey] =
                ((entry[countKey] as number | undefined) ?? 0) + 1;
        }

        evaluated.forEach((item) => {
            const dateStr = new Date(item.target_date).toLocaleDateString();
            const entry = getOrCreateEntry(dateStr, item.target_date);
            const score =
                ((item.sector_percentile_score || 0) + (item.pair_percentile_score || 0)) / 2;
            updateEntryScore(entry, item.model_name, score);
        });

        const modelKeys: { key: ModelKey; sumKey: keyof ChartEntry; countKey: keyof ChartEntry }[] =
            [
                { key: 'deepseek', sumKey: 'deepseekSum', countKey: 'deepseekCount' },
                { key: 'minimax', sumKey: 'minimaxSum', countKey: 'minimaxCount' },
                { key: 'gemini', sumKey: 'geminiSum', countKey: 'geminiCount' },
                { key: 'openai', sumKey: 'openaiSum', countKey: 'openaiCount' },
            ];

        // Compute averages
        dateMap.forEach((entry) => {
            modelKeys.forEach(({ key, sumKey, countKey }) => {
                const count = entry[countKey] as number | undefined;
                if (count && count > 0) {
                    entry[key] = ((entry[sumKey] as number | undefined) ?? 0) / count;
                }
            });
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

        // Scales with single data point padding
        const extent = d3.extent(chartData, (d) => d.date) as [Date, Date];
        if (extent[0] && extent[1] && extent[0].getTime() === extent[1].getTime()) {
            extent[0] = new Date(extent[0].getTime() - 24 * 60 * 60 * 1000);
            extent[1] = new Date(extent[1].getTime() + 24 * 60 * 60 * 1000);
        }

        const x = d3.scaleTime().domain(extent).range([0, width]);

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
        type ModelKey = 'deepseek' | 'minimax' | 'gemini' | 'openai';
        const lineGenerator = (key: ModelKey) =>
            d3
                .line<ChartEntry>()
                .defined((d) => d[key] !== undefined)
                .x((d) => x(d.date))
                .y((d) => y(d[key] ?? 0));

        // Model Series Configurations
        const seriesConfig: { key: ModelKey; label: string; color: string }[] = [
            { key: 'deepseek', label: 'DeepSeek Flash', color: '#60a5fa' },
            { key: 'minimax', label: 'MiniMax-M3', color: '#34d399' },
            { key: 'gemini', label: 'Gemini 3.5', color: '#f59e0b' },
            { key: 'openai', label: 'OpenAI GPT-5.6', color: '#a855f7' },
        ];

        // Render lines and dots for each model series
        seriesConfig.forEach(({ key, color }) => {
            svg.append('path')
                .datum(chartData)
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 3)
                .attr('d', lineGenerator(key));

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
        });

        // Legend
        const legend = svg.append('g').attr('transform', `translate(${width - 150}, 0)`);

        seriesConfig.forEach(({ label, color }, i) => {
            const yOffset = i * 20;
            legend
                .append('circle')
                .attr('cx', 0)
                .attr('cy', yOffset)
                .attr('r', 5)
                .style('fill', color);
            legend
                .append('text')
                .attr('x', 10)
                .attr('y', yOffset + 4)
                .text(label)
                .style('fill', '#f8fafc')
                .style('font-size', '12px')
                .attr('alignment-baseline', 'middle');
        });
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
