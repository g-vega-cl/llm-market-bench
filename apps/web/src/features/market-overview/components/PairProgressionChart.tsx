import * as d3 from 'd3';
import * as React from 'react';
import type { PairHistoryPoint } from '../api/fetch-pair-history';
import { etfDescriptions } from '../utils/etf-descriptions';

const formatReturn = (val: number | null): string => {
    if (val === null) return 'N/A';
    const sign = val > 0 ? '+' : '';
    return `${sign}${val.toFixed(2)}%`;
};

interface PairProgressionChartProps {
    data: PairHistoryPoint[];
    tickerA: string;
    tickerB: string;
}

export function PairProgressionChart({ data, tickerA, tickerB }: PairProgressionChartProps) {
    const svgRef = React.useRef<SVGSVGElement>(null);
    const containerRef = React.useRef<HTMLDivElement>(null);

    const [hoveredPoint, setHoveredPoint] = React.useState<PairHistoryPoint | null>(null);

    React.useEffect(() => {
        if (!data || data.length === 0 || !svgRef.current) return;

        const margin = { top: 30, right: 60, bottom: 40, left: 60 };
        const width = 800 - margin.left - margin.right;
        const height = 360 - margin.top - margin.bottom;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        interface ChartPoint {
            date: Date;
            pearson: number | null;
            spearman: number | null;
            returnA: number | null;
            returnB: number | null;
            raw: PairHistoryPoint;
        }

        // Parsed time-series data
        const chartData: ChartPoint[] = data.map((d) => ({
            date: new Date(d.run_date),
            pearson: d.pearson_corr !== null ? Number(d.pearson_corr) : null,
            spearman: d.spearman_corr !== null ? Number(d.spearman_corr) : null,
            returnA: d.returns_a_90d !== null ? Number(d.returns_a_90d) : null,
            returnB: d.returns_b_90d !== null ? Number(d.returns_b_90d) : null,
            raw: d,
        }));

        // 1. Scales
        const x = d3
            .scaleTime()
            .domain(d3.extent(chartData, (d) => d.date) as [Date, Date])
            .range([0, width]);

        // Left axis: Correlation (-1.0 to +1.0)
        const yLeft = d3.scaleLinear().domain([-1.0, 1.0]).range([height, 0]);

        // Right axis: Trailing Returns
        const allReturns = chartData.flatMap((d) =>
            [d.returnA, d.returnB].filter((v): v is number => v !== null),
        );
        const minReturn = d3.min(allReturns) ?? -10;
        const maxReturn = d3.max(allReturns) ?? 10;
        const yRight = d3
            .scaleLinear()
            .domain([minReturn - 5, maxReturn + 5])
            .nice()
            .range([height, 0]);

        // 2. Axes & Grids
        // Horizontal Grid Lines (using yLeft)
        g.append('g')
            .attr('class', 'grid opacity-5 dark:opacity-10')
            .call(
                d3
                    .axisLeft(yLeft)
                    .tickSize(-width)
                    .tickFormat(() => ''),
            )
            .attr('color', 'currentColor');

        // X Axis
        g.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(
                d3
                    .axisBottom(x)
                    .ticks(5)
                    .tickFormat((d) => d3.timeFormat('%b %d')(d as Date)),
            )
            .attr('color', '#94a3b8')
            .selectAll('text')
            .attr('class', 'text-xs font-medium')
            .attr('dy', '1em');

        // Left Y Axis (Correlation)
        g.append('g')
            .call(d3.axisLeft(yLeft).ticks(5).tickFormat(d3.format('.1f')))
            .attr('color', '#3b82f6') // Blue axis
            .selectAll('text')
            .attr('class', 'text-xs font-semibold');

        // Left Axis Title
        g.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('y', -45)
            .attr('x', -height / 2)
            .attr('text-anchor', 'middle')
            .attr(
                'class',
                'text-[10px] font-black uppercase tracking-wider fill-blue-500 dark:fill-blue-400',
            )
            .text('Correlation (Pearson)');

        // Right Y Axis (Returns)
        g.append('g')
            .attr('transform', `translate(${width}, 0)`)
            .call(
                d3
                    .axisRight(yRight)
                    .ticks(5)
                    .tickFormat((d) => `${d}%`),
            )
            .attr('color', '#10b981') // Green axis
            .selectAll('text')
            .attr('class', 'text-xs font-semibold');

        // Right Axis Title
        g.append('text')
            .attr('transform', 'rotate(90)')
            .attr('y', -width - 45)
            .attr('x', height / 2)
            .attr('text-anchor', 'middle')
            .attr(
                'class',
                'text-[10px] font-black uppercase tracking-wider fill-emerald-500 dark:fill-emerald-400',
            )
            .text('90D Trailing Return (%)');

        // Zero-correlation marker line
        g.append('line')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', yLeft(0))
            .attr('y2', yLeft(0))
            .attr('stroke', '#94a3b8')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '3,3')
            .attr('opacity', 0.4);

        // 3. Line Generators
        const pearsonLine = d3
            .line<ChartPoint>()
            .defined((d) => d.pearson !== null)
            .x((d) => x(d.date))
            .y((d) => yLeft(d.pearson ?? 0))
            .curve(d3.curveMonotoneX);

        const returnALine = d3
            .line<ChartPoint>()
            .defined((d) => d.returnA !== null)
            .x((d) => x(d.date))
            .y((d) => yRight(d.returnA ?? 0))
            .curve(d3.curveMonotoneX);

        const returnBLine = d3
            .line<ChartPoint>()
            .defined((d) => d.returnB !== null)
            .x((d) => x(d.date))
            .y((d) => yRight(d.returnB ?? 0))
            .curve(d3.curveMonotoneX);

        // 4. Draw Lines with premium gradients and filters
        // Pearson Line
        g.append('path')
            .datum(chartData)
            .attr('fill', 'none')
            .attr('stroke', 'url(#correlation-grad)')
            .attr('stroke-width', 3)
            .attr('d', pearsonLine);

        // Ticker A Returns Line (Dashed)
        g.append('path')
            .datum(chartData)
            .attr('fill', 'none')
            .attr('stroke', '#10b981')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '4,2')
            .attr('opacity', 0.75)
            .attr('d', returnALine);

        // Ticker B Returns Line (Dashed)
        g.append('path')
            .datum(chartData)
            .attr('fill', 'none')
            .attr('stroke', '#f59e0b')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '4,2')
            .attr('opacity', 0.75)
            .attr('d', returnBLine);

        // Define premium HSL gradients
        const defs = svg.append('defs');
        const linearGradient = defs
            .append('linearGradient')
            .attr('id', 'correlation-grad')
            .attr('x1', '0%')
            .attr('y1', '0%')
            .attr('x2', '100%')
            .attr('y2', '0%');

        linearGradient.append('stop').attr('offset', '0%').attr('stop-color', '#3b82f6'); // bright sky blue

        linearGradient.append('stop').attr('offset', '100%').attr('stop-color', '#a855f7'); // deep purple

        // 5. Interactive Guideline Overlay
        const trackingLine = g
            .append('line')
            .attr('class', 'guideline opacity-0')
            .attr('y1', 0)
            .attr('y2', height)
            .attr('stroke', '#64748b')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '2,2');

        const bisectDate = d3.bisector<ChartPoint, Date>((d) => d.date).left;

        // Overlay rect to catch pointer events
        g.append('rect')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', 'transparent')
            .on('pointermove mousemove', (event) => {
                const mouseX = d3.pointer(event)[0];
                const hoveredDate = x.invert(mouseX);

                // Bisect to find nearest point
                const index = bisectDate(chartData, hoveredDate, 1);
                const d0 = chartData[index - 1];
                const d1 = chartData[index];
                if (!d0) return;

                const pointObj =
                    d1 &&
                    hoveredDate.getTime() - d0.date.getTime() >
                        d1.date.getTime() - hoveredDate.getTime()
                        ? d1
                        : d0;

                // Update tracking line position
                const pointX = x(pointObj.date);
                trackingLine.attr('opacity', 1).attr('x1', pointX).attr('x2', pointX);

                setHoveredPoint(pointObj.raw);
            })
            .on('pointerleave mouseleave', () => {
                trackingLine.attr('opacity', 0);
                setHoveredPoint(null);
            });
    }, [data]);

    const displayPoint = hoveredPoint || (data.length > 0 ? data[data.length - 1] : null);

    const getCorrelationColor = (val: number | null) => {
        if (val === null) return 'text-zinc-400 dark:text-zinc-500';
        const absVal = Math.abs(val);
        if (absVal < 0.35) return 'text-emerald-500 dark:text-emerald-400'; // Highly uncorrelated
        if (val < 0) return 'text-blue-500 dark:text-blue-400'; // Diversifier
        return 'text-amber-500 dark:text-amber-400'; // Highly correlated
    };

    return (
        <div
            ref={containerRef}
            className="relative w-full overflow-hidden bg-white dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800/80 rounded-3xl p-6 shadow-xl"
        >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <div>
                    <h4 className="text-md font-black tracking-tight text-zinc-900 dark:text-white uppercase">
                        Weekly Correlation & Returns Timeline
                    </h4>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        Pearson correlation coefficient (solid) against 90-day returns of {tickerA}{' '}
                        and {tickerB} (dashed).
                    </p>
                </div>

                {/* Custom styled legend */}
                <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
                    <div className="flex items-center gap-2">
                        <span className="w-4 h-1 rounded bg-gradient-to-r from-blue-500 to-purple-500" />
                        <span className="font-semibold text-zinc-600 dark:text-zinc-300">
                            Correlation
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-4 h-0.5 border-t-2 border-dashed border-emerald-500" />
                        <span className="font-mono text-zinc-750 dark:text-zinc-300">
                            {tickerA} Return
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-4 h-0.5 border-t-2 border-dashed border-amber-500" />
                        <span className="font-mono text-zinc-750 dark:text-zinc-300">
                            {tickerB} Return
                        </span>
                    </div>
                </div>
            </div>

            {/* Premium Cursor Metrics Status Board (Defaults to latest week in timeline) */}
            {displayPoint && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 p-4 mb-6 bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800/60 rounded-2xl shadow-inner font-sans animate-scale-in">
                    {/* Run Date */}
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
                            Timeline Week
                        </span>
                        <span className="text-xs sm:text-sm font-black text-zinc-850 dark:text-zinc-200 mt-1 uppercase">
                            {new Date(displayPoint.run_date).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                                timeZone: 'UTC',
                            })}
                        </span>
                    </div>

                    {/* Pearson / Spearman Correlation */}
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
                            Pearson / Spearman
                        </span>
                        <span className="text-xs sm:text-sm font-black font-mono mt-1">
                            <span className={getCorrelationColor(displayPoint.pearson_corr)}>
                                {displayPoint.pearson_corr !== null
                                    ? displayPoint.pearson_corr.toFixed(3)
                                    : 'N/A'}
                            </span>
                            <span className="text-zinc-300 dark:text-zinc-700 mx-1">/</span>
                            <span className="text-zinc-500 dark:text-zinc-400">
                                {displayPoint.spearman_corr !== null
                                    ? displayPoint.spearman_corr.toFixed(3)
                                    : 'N/A'}
                            </span>
                        </span>
                    </div>

                    {/* Asset A return */}
                    <div className="flex flex-col">
                        <span
                            className="text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500 truncate"
                            title={`${tickerA} (${etfDescriptions[tickerA] || 'ETF'})`}
                        >
                            {tickerA} ({etfDescriptions[tickerA] || 'ETF'})
                        </span>
                        <span
                            className={`text-xs sm:text-sm font-black font-mono mt-1 ${
                                displayPoint.returns_a_90d !== null &&
                                displayPoint.returns_a_90d >= 0
                                    ? 'text-emerald-500'
                                    : 'text-red-500'
                            }`}
                        >
                            {formatReturn(displayPoint.returns_a_90d)}
                        </span>
                    </div>

                    {/* Asset B return */}
                    <div className="flex flex-col">
                        <span
                            className="text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500 truncate"
                            title={`${tickerB} (${etfDescriptions[tickerB] || 'ETF'})`}
                        >
                            {tickerB} ({etfDescriptions[tickerB] || 'ETF'})
                        </span>
                        <span
                            className={`text-xs sm:text-sm font-black font-mono mt-1 ${
                                displayPoint.returns_b_90d !== null &&
                                displayPoint.returns_b_90d >= 0
                                    ? 'text-emerald-500'
                                    : 'text-red-500'
                            }`}
                        >
                            {formatReturn(displayPoint.returns_b_90d)}
                        </span>
                    </div>
                </div>
            )}

            <div className="relative overflow-x-auto select-none">
                <svg
                    ref={svgRef}
                    viewBox="0 0 800 360"
                    width="100%"
                    height="100%"
                    className="overflow-visible min-w-[700px]"
                />
            </div>
        </div>
    );
}
