import type { PortfolioPerformance } from '@llm-market-bench/database';
import * as d3 from 'd3';
import * as React from 'react';
import type { BenchmarkDataPoint } from '../api/fetch-portfolios';
import { BENCHMARK_OPTIONS } from './BenchmarkSelector';

export type PerformanceSnapshot = Pick<PortfolioPerformance, 'date' | 'total_equity'>;

interface PerformanceChartProps {
    data: PerformanceSnapshot[];
    benchmarkData?: Record<string, BenchmarkDataPoint[]>;
    selectedBenchmark?: string;
    showPercentage?: boolean;
}

interface ChartLine {
    date: Date;
    value: number;
    ticker?: string;
}

function normalizeToPercentage(data: ChartLine[], baseDate: Date, baseValue: number): ChartLine[] {
    if (baseValue === 0) return data;
    return data.map((d) => ({
        ...d,
        value: ((d.value - baseValue) / baseValue) * 100,
    }));
}

export function PerformanceChart({
    data,
    benchmarkData,
    selectedBenchmark,
    showPercentage = false,
}: PerformanceChartProps) {
    const svgRef = React.useRef<SVGSVGElement>(null);
    const [tooltipData, setTooltipData] = React.useState<{
        date: string;
        equity: number;
        benchmarkValue?: number;
        benchmarkTicker?: string;
        x: number;
        y: number;
        outperformance?: number;
    } | null>(null);

    React.useEffect(() => {
        if (!data || data.length === 0 || !svgRef.current) return;

        const margin = { top: 20, right: 120, bottom: 30, left: 60 };
        const width = 800 - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        const parsedData: ChartLine[] = data.map((d) => ({
            date: new Date(d.date),
            value: Number(d.total_equity),
        }));

        let allLines: ChartLine[] = parsedData;
        let benchmarkLines: ChartLine[] = [];

        if (selectedBenchmark && benchmarkData && benchmarkData[selectedBenchmark]) {
            benchmarkLines = benchmarkData[selectedBenchmark].map((d) => ({
                date: new Date(d.date),
                value: d.price,
                ticker: selectedBenchmark,
            }));
        }

        const usePercentage = showPercentage && (selectedBenchmark || benchmarkLines.length > 0);
        const benchmarkOption = BENCHMARK_OPTIONS.find((b) => b.ticker === selectedBenchmark);
        const benchmarkLabel = benchmarkOption ? benchmarkOption.label : (selectedBenchmark ?? '');

        if (usePercentage) {
            const portfolioBase = parsedData[0]?.value || 1;
            const benchmarkBase = benchmarkLines[0]?.value || 1;

            allLines = normalizeToPercentage(parsedData, parsedData[0].date, portfolioBase);
            if (benchmarkLines.length > 0) {
                benchmarkLines = normalizeToPercentage(
                    benchmarkLines,
                    benchmarkLines[0].date,
                    benchmarkBase,
                );
            }
        }

        const allValues = [...allLines.map((d) => d.value), ...benchmarkLines.map((d) => d.value)];

        const x = d3
            .scaleTime()
            .domain(d3.extent(allLines, (d) => d.date) as [Date, Date])
            .range([0, width]);

        const y = d3
            .scaleLinear()
            .domain([
                d3.min(allValues, (d) => d) || (usePercentage ? -10 : 0),
                d3.max(allValues, (d) => d) || (usePercentage ? 10 : 10000),
            ])
            .nice()
            .range([height, 0]);

        const line = d3
            .line<ChartLine>()
            .x((d) => x(d.date))
            .y((d) => y(d.value))
            .curve(d3.curveMonotoneX);

        g.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x).ticks(5))
            .attr('color', '#94a3b8');

        g.append('g')
            .call(
                d3
                    .axisLeft(y)
                    .tickFormat((d) =>
                        usePercentage
                            ? `${Number(d) > 0 ? '+' : ''}${Number(d).toFixed(1)}%`
                            : `$${Number(d).toLocaleString()}`,
                    ),
            )
            .attr('color', '#94a3b8');

        g.append('g')
            .attr('class', 'grid')
            .attr('opacity', 0.1)
            .call(
                d3
                    .axisLeft(y)
                    .tickSize(-width)
                    .tickFormat(() => ''),
            );

        if (usePercentage) {
            g.append('line')
                .attr('x1', 0)
                .attr('x2', width)
                .attr('y1', y(0))
                .attr('y2', y(0))
                .attr('stroke', '#a1a1aa')
                .attr('stroke-width', 1)
                .attr('stroke-dasharray', '4,4');
        }

        g.append('path')
            .datum(allLines)
            .attr('fill', 'none')
            .attr('stroke', '#0ea5e9')
            .attr('stroke-width', 2.5)
            .attr('d', line);

        const area = d3
            .area<ChartLine>()
            .x((d) => x(d.date))
            .y0(height)
            .y1((d) => y(d.value))
            .curve(d3.curveMonotoneX);

        g.append('path').datum(allLines).attr('fill', 'url(#line-gradient)').attr('d', area);

        if (benchmarkLines.length > 0) {
            g.append('path')
                .datum(benchmarkLines)
                .attr('fill', 'none')
                .attr('stroke', '#f59e0b')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '6,3')
                .attr('d', line);
        }

        const gradient = svg
            .append('defs')
            .append('linearGradient')
            .attr('id', 'line-gradient')
            .attr('x1', '0%')
            .attr('y1', '0%')
            .attr('x2', '0%')
            .attr('y2', '100%');

        gradient
            .append('stop')
            .attr('offset', '0%')
            .attr('stop-color', '#0ea5e9')
            .attr('stop-opacity', 0.2);

        gradient
            .append('stop')
            .attr('offset', '100%')
            .attr('stop-color', '#0ea5e9')
            .attr('stop-opacity', 0);

        if (benchmarkLines.length > 0) {
            const legendGradient = svg
                .append('defs')
                .append('linearGradient')
                .attr('id', 'benchmark-gradient')
                .attr('x1', '0%')
                .attr('y1', '0%')
                .attr('x2', '0%')
                .attr('y2', '100%');

            legendGradient
                .append('stop')
                .attr('offset', '0%')
                .attr('stop-color', '#f59e0b')
                .attr('stop-opacity', 0.15);

            legendGradient
                .append('stop')
                .attr('offset', '100%')
                .attr('stop-color', '#f59e0b')
                .attr('stop-opacity', 0);
        }

        const bisector = d3.bisector<ChartLine, Date>((d) => d.date).left;

        const overlay = g
            .append('rect')
            .attr('class', 'overlay')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', 'none')
            .attr('pointer-events', 'all')
            .on('mousemove', (event) => {
                const [mouseX] = d3.pointer(event);
                const x0 = bisector(allLines, x.invert(mouseX), 1);
                const d0 = allLines[x0 - 1];
                const d1 = allLines[x0];
                const portfolioPt =
                    d0 && d1 ? (mouseX - x(d0.date) < x(d1.date) - mouseX ? d0 : d1) : d0 || d1;

                let benchmarkPt: ChartLine | undefined;
                let outperformance: number | undefined;

                if (benchmarkLines.length > 0 && selectedBenchmark) {
                    const bX0 = bisector(benchmarkLines, x.invert(mouseX), 1);
                    const bD0 = benchmarkLines[bX0 - 1];
                    const bD1 = benchmarkLines[bX0];
                    benchmarkPt =
                        bD0 && bD1
                            ? mouseX - x(bD0.date) < x(bD1.date) - mouseX
                                ? bD0
                                : bD1
                            : bD0 || bD1;

                    if (portfolioPt && benchmarkPt && usePercentage) {
                        outperformance = portfolioPt.value - benchmarkPt.value;
                    }
                }

                if (portfolioPt) {
                    setTooltipData({
                        date: portfolioPt.date.toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                        }),
                        equity: portfolioPt.value,
                        benchmarkValue: benchmarkPt?.value,
                        benchmarkTicker: benchmarkPt?.ticker,
                        x: x(portfolioPt.date),
                        y: y(portfolioPt.value),
                        outperformance,
                    });
                }
            })
            .on('mouseleave', () => {
                setTooltipData(null);
            });

        const crosshair = g
            .append('line')
            .attr('class', 'crosshair')
            .attr('stroke', '#64748b')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '4,4')
            .attr('opacity', 0)
            .attr('x1', 0)
            .attr('x2', 0)
            .attr('y1', 0)
            .attr('y2', height);

        const dot = g
            .append('circle')
            .attr('class', 'dot')
            .attr('r', 6)
            .attr('fill', '#0ea5e9')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .attr('opacity', 0);

        const benchmarkDot = g
            .append('circle')
            .attr('class', 'benchmark-dot')
            .attr('r', 5)
            .attr('fill', '#f59e0b')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .attr('opacity', 0);

        if (benchmarkLines.length > 0) {
            svg.select('.crosshair')
                .attr('opacity', 1)
                .attr('transform', `translate(${tooltipData?.x || 0},0)`);
        }

        const legend = g.append('g').attr('transform', `translate(${width + 20}, 20)`);

        if (benchmarkLines.length > 0) {
            legend
                .append('line')
                .attr('x1', 0)
                .attr('x2', 20)
                .attr('y1', 0)
                .attr('y2', 0)
                .attr('stroke', '#0ea5e9')
                .attr('stroke-width', 2.5);

            legend
                .append('text')
                .attr('x', 28)
                .attr('y', 4)
                .attr('font-size', '12px')
                .attr('fill', '#0ea5e9')
                .text('Portfolio');

            legend
                .append('line')
                .attr('x1', 0)
                .attr('x2', 20)
                .attr('y1', 20)
                .attr('y2', 20)
                .attr('stroke', '#f59e0b')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '6,3');

            legend
                .append('text')
                .attr('x', 28)
                .attr('y', 24)
                .attr('font-size', '12px')
                .attr('fill', '#f59e0b')
                .text(String(benchmarkLabel));
        }
    }, [data, benchmarkData, selectedBenchmark, showPercentage]);

    React.useEffect(() => {
        if (!svgRef.current || !tooltipData) return;

        const svg = d3.select(svgRef.current);

        svg.select('.crosshair')
            .attr('opacity', 1)
            .attr('transform', `translate(${tooltipData.x},0)`);

        svg.select('.dot').attr('opacity', 1).attr('cx', tooltipData.x).attr('cy', tooltipData.y);

        const benchmarkDot = svg.select('.benchmark-dot');
        if (tooltipData.benchmarkValue !== undefined && selectedBenchmark) {
            const benchmarkPrices = benchmarkData?.[selectedBenchmark] || [];
            const baseValue = Number(data[0]?.total_equity) || 1;
            const benchmarkBase = benchmarkPrices[0]?.price || 1;

            const portfolioPct = ((tooltipData.equity - baseValue) / baseValue) * 100;
            const benchmarkPct =
                ((tooltipData.benchmarkValue - benchmarkBase) / benchmarkBase) * 100;
            const outperformance = portfolioPct - benchmarkPct;

            const yPos = yScale(outperformance);

            benchmarkDot.attr('opacity', 1).attr('cx', tooltipData.x).attr('cy', yPos);
        } else {
            benchmarkDot.attr('opacity', 0);
        }

        function yScale(val: number): number {
            const margin = { top: 20, right: 120, bottom: 30, left: 60 };
            const height = 400 - margin.top - margin.bottom;
            const allValues = data.map((d) => Number(d.total_equity));
            const minVal = Math.min(...allValues, 0);
            const maxVal = Math.max(...allValues, 10000);
            const y = d3.scaleLinear().domain([minVal, maxVal]).range([height, 0]);
            return y(val);
        }
    }, [tooltipData, selectedBenchmark, benchmarkData, data]);

    const hasBenchmark = selectedBenchmark && benchmarkData && benchmarkData[selectedBenchmark];

    const getLatestWithBenchmark = () => {
        if (data.length === 0) return null;

        const latestDate = data[data.length - 1].date;
        const equity = Number(data[data.length - 1].total_equity);

        if (!selectedBenchmark || !benchmarkData?.[selectedBenchmark]) {
            return { date: latestDate, equity, x: 0, y: 0 };
        }

        const benchmarkPoints = benchmarkData[selectedBenchmark];
        const benchmarkPoint =
            benchmarkPoints.find((p) => p.date === latestDate) ||
            benchmarkPoints[benchmarkPoints.length - 1];

        let portfolioChange: number | undefined;
        let benchmarkChange: number | undefined;
        let outperformance: number | undefined;

        if (showPercentage && benchmarkPoint && data.length > 0) {
            const portfolioStart = Number(data[0].total_equity) || 1;
            const benchmarkStart = benchmarkPoints[0]?.price || 1;
            portfolioChange = ((equity - portfolioStart) / portfolioStart) * 100;
            benchmarkChange = ((benchmarkPoint.price - benchmarkStart) / benchmarkStart) * 100;
            outperformance = portfolioChange - benchmarkChange;
        }

        return {
            date: latestDate,
            equity: portfolioChange ?? equity,
            benchmarkValue: benchmarkChange ?? benchmarkPoint?.price,
            benchmarkTicker: selectedBenchmark,
            outperformance,
            x: 0,
            y: 0,
        };
    };

    const displayData = tooltipData || getLatestWithBenchmark();

    return (
        <div className="w-full bg-white border border-zinc-200 rounded-xl p-4 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-wider">
                    {showPercentage && hasBenchmark ? 'Performance vs Benchmark' : 'Equity Curve'}
                </h3>
                {hasBenchmark && (
                    <div className="text-xs text-zinc-400">Normalized to percentage returns</div>
                )}
            </div>
            {displayData && (
                <div className="mb-4 p-3 bg-zinc-50 rounded-lg border border-zinc-100">
                    <div className="text-xs text-zinc-500 mb-1">{displayData.date}</div>
                    <div className="flex items-baseline gap-3">
                        <span className="text-xl font-bold text-sky-600">
                            {showPercentage && hasBenchmark
                                ? `${displayData.equity > 0 ? '+' : ''}${displayData.equity.toFixed(2)}%`
                                : `$${displayData.equity.toLocaleString(undefined, {
                                      minimumFractionDigits: 2,
                                      maximumFractionDigits: 2,
                                  })}`}
                        </span>
                    </div>
                    {displayData.benchmarkValue !== undefined && (
                        <div className="mt-2 pt-2 border-t border-zinc-200">
                            <div className="text-sm text-amber-600">
                                {
                                    BENCHMARK_OPTIONS.find((b) => b.ticker === selectedBenchmark)
                                        ?.label
                                }
                                :{' '}
                                {showPercentage
                                    ? `${displayData.benchmarkValue > 0 ? '+' : ''}${displayData.benchmarkValue.toFixed(2)}%`
                                    : `$${displayData.benchmarkValue?.toLocaleString()}`}
                            </div>
                            {displayData.outperformance !== undefined && (
                                <div
                                    className={`text-xs mt-1 ${displayData.outperformance >= 0 ? 'text-emerald-600' : 'text-red-600'}`}
                                >
                                    {displayData.outperformance >= 0 ? '+' : ''}
                                    {displayData.outperformance.toFixed(2)}% outperformance
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
            <div className="w-full overflow-x-auto relative">
                <svg
                    ref={svgRef}
                    width="100%"
                    height="400"
                    viewBox="0 0 800 400"
                    preserveAspectRatio="xMidYMid meet"
                />
            </div>
        </div>
    );
}
