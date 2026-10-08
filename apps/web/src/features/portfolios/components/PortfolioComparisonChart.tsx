import { Button } from '@llm-market-bench/ui-design-system';
import * as d3 from 'd3';
import * as React from 'react';
import type { BenchmarkDataPoint } from '../api/fetch-portfolios';
import { BENCHMARK_OPTIONS } from './BenchmarkSelector';
import { PortfolioComparisonSelector } from './PortfolioComparisonSelector';

const PORTFOLIO_COLORS = ['#0ea5e9', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4'];

interface PortfolioSeries {
    portfolioId: string;
    ownerId: string;
    performance: { date: string; value: number }[];
}

interface TooltipData {
    date: string;
    portfolioValues: { ownerId: string; value: number; color: string }[];
    benchmarkValue?: number;
    benchmarkTicker?: string;
    x: number;
    y: number;
}

interface ChartLine {
    date: Date;
    value: number;
    portfolioId?: string;
    ticker?: string;
    color?: string;
}

interface PortfolioComparisonChartProps {
    data: PortfolioSeries[];
    benchmarkData?: Record<string, BenchmarkDataPoint[]>;
    selectedBenchmark?: string;
    onReset?: () => void;
    maxSelected?: number;
}

export function PortfolioComparisonChart({
    data: rawData,
    benchmarkData: rawBenchmarkData,
    selectedBenchmark = 'SPY',
    onReset,
    maxSelected = 5,
}: PortfolioComparisonChartProps) {
    const data = React.useMemo(() => {
        return rawData.map((portfolio) => {
            const cleanedPerformance = portfolio.performance
                .map((p) => ({
                    date: p.date,
                    value: p.value,
                }))
                .filter((d) => {
                    const parsedDate = new Date(d.date);
                    return (
                        d.date &&
                        d.date !== 'invalid-date' &&
                        parsedDate instanceof Date &&
                        !Number.isNaN(parsedDate.getTime()) &&
                        d.value !== null &&
                        !Number.isNaN(d.value)
                    );
                });

            const dateMap = new Map<string, { date: string; value: number }>();
            cleanedPerformance.forEach((pt) => {
                const parsedDate = new Date(pt.date);
                const dateKey = parsedDate.toISOString().split('T')[0];
                dateMap.set(dateKey, pt);
            });

            const deduplicated = Array.from(dateMap.values()).sort(
                (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
            );

            return {
                ...portfolio,
                performance: deduplicated,
            };
        });
    }, [rawData]);

    const benchmarkData = React.useMemo(() => {
        if (!rawBenchmarkData) return undefined;
        const result: Record<string, BenchmarkDataPoint[]> = {};
        for (const ticker of Object.keys(rawBenchmarkData)) {
            const points = rawBenchmarkData[ticker] || [];
            const cleanedPoints = points.filter((d) => {
                const parsedDate = new Date(d.date);
                return (
                    d.date &&
                    d.date !== 'invalid-benchmark-date' &&
                    parsedDate instanceof Date &&
                    !Number.isNaN(parsedDate.getTime()) &&
                    d.price !== null &&
                    !Number.isNaN(d.price)
                );
            });

            const dateMap = new Map<string, BenchmarkDataPoint>();
            cleanedPoints.forEach((pt) => {
                const parsedDate = new Date(pt.date);
                const dateKey = parsedDate.toISOString().split('T')[0];
                dateMap.set(dateKey, pt);
            });

            const deduplicated = Array.from(dateMap.values()).sort(
                (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
            );

            result[ticker] = deduplicated;
        }
        return result;
    }, [rawBenchmarkData]);

    const svgRef = React.useRef<SVGSVGElement>(null);
    const [clickedData, setClickedData] = React.useState<TooltipData | null>(null);
    const [latestData, setLatestData] = React.useState<TooltipData | null>(null);

    const defaultSelectedIds = React.useMemo(() => {
        const withData = data.filter((p) => p.performance.length > 0);
        const source = withData.length > 0 ? withData : data;
        return source.slice(0, maxSelected).map((p) => p.portfolioId);
    }, [data, maxSelected]);

    const isInitializedRef = React.useRef(defaultSelectedIds.length > 0);
    const [selectedPortfolioIds, setSelectedPortfolioIds] = React.useState<string[]>(
        () => defaultSelectedIds,
    );

    React.useEffect(() => {
        if (!isInitializedRef.current && defaultSelectedIds.length > 0) {
            setSelectedPortfolioIds(defaultSelectedIds);
            isInitializedRef.current = true;
        } else if (isInitializedRef.current) {
            setSelectedPortfolioIds((prev) =>
                prev.filter((id) => data.some((p) => p.portfolioId === id)),
            );
        }
    }, [defaultSelectedIds, data]);

    const handleAddPortfolio = React.useCallback(
        (portfolioId: string) => {
            setSelectedPortfolioIds((prev) => {
                if (prev.includes(portfolioId) || prev.length >= maxSelected) return prev;
                return [...prev, portfolioId];
            });
        },
        [maxSelected],
    );

    const handleRemovePortfolio = React.useCallback((portfolioId: string) => {
        setSelectedPortfolioIds((prev) => prev.filter((id) => id !== portfolioId));
    }, []);

    const handleResetSelection = React.useCallback(() => {
        setSelectedPortfolioIds(defaultSelectedIds);
    }, [defaultSelectedIds]);

    const isCustomSelection = React.useMemo(() => {
        if (selectedPortfolioIds.length !== defaultSelectedIds.length) return true;
        const defaultSet = new Set(defaultSelectedIds);
        return selectedPortfolioIds.some((id) => !defaultSet.has(id));
    }, [selectedPortfolioIds, defaultSelectedIds]);

    const activeData = React.useMemo(() => {
        const currentIds =
            selectedPortfolioIds.length > 0 || isInitializedRef.current
                ? selectedPortfolioIds
                : defaultSelectedIds;
        return data.filter((p) => currentIds.includes(p.portfolioId));
    }, [data, selectedPortfolioIds, defaultSelectedIds]);

    const portfolioColors = React.useMemo(() => {
        const colors: Record<string, string> = {};
        activeData.forEach((portfolio, index) => {
            colors[portfolio.portfolioId] = PORTFOLIO_COLORS[index % PORTFOLIO_COLORS.length];
        });
        return colors;
    }, [activeData]);

    const dateRange = React.useMemo(() => {
        if (activeData.length === 0) {
            if (selectedBenchmark && benchmarkData?.[selectedBenchmark]?.length) {
                const bDates = benchmarkData[selectedBenchmark].map((b) => new Date(b.date));
                return d3.extent(bDates) as [Date, Date];
            }
            return [new Date(), new Date()] as [Date, Date];
        }
        const allDates = activeData.flatMap((p) => p.performance.map((pp) => new Date(pp.date)));
        if (allDates.length === 0) return [new Date(), new Date()] as [Date, Date];
        return d3.extent(allDates) as [Date, Date];
    }, [activeData, selectedBenchmark, benchmarkData]);

    const getLatestData = React.useCallback((): TooltipData | null => {
        if (activeData.length === 0 && !selectedBenchmark) return null;

        const portfolioValues: { ownerId: string; value: number; color: string }[] = [];

        activeData.forEach((portfolio, index) => {
            if (portfolio.performance.length === 0) return;

            const latest = portfolio.performance[portfolio.performance.length - 1];
            portfolioValues.push({
                ownerId: portfolio.ownerId,
                value: latest.value,
                color:
                    portfolioColors[portfolio.portfolioId] ||
                    PORTFOLIO_COLORS[index % PORTFOLIO_COLORS.length],
            });
        });

        let benchmarkValue: number | undefined;
        if (selectedBenchmark && benchmarkData?.[selectedBenchmark]) {
            const bPoints = benchmarkData[selectedBenchmark];
            if (bPoints.length > 0) {
                const latest = bPoints[bPoints.length - 1];
                const base = bPoints[0].price || 1;
                benchmarkValue = ((latest.price - base) / base) * 100;
            }
        }

        const latestDate = activeData.reduce((latest, portfolio) => {
            if (portfolio.performance.length === 0) return latest;
            const d = portfolio.performance[portfolio.performance.length - 1].date;
            return !latest || d > latest ? d : latest;
        }, '');

        return {
            date: latestDate,
            portfolioValues: portfolioValues,
            benchmarkValue,
            benchmarkTicker: selectedBenchmark,
            x: 0,
            y: 0,
        };
    }, [activeData, portfolioColors, benchmarkData, selectedBenchmark]);

    React.useEffect(() => {
        setClickedData((prev) => {
            if (!prev) return null;
            const remaining = prev.portfolioValues.filter((pv) =>
                selectedPortfolioIds.some((id) => {
                    const p = data.find((d) => d.portfolioId === id);
                    return p?.ownerId === pv.ownerId;
                }),
            );
            if (remaining.length === 0 && !prev.benchmarkValue) {
                return null;
            }
            return { ...prev, portfolioValues: remaining };
        });
    }, [selectedPortfolioIds, data]);

    React.useEffect(() => {
        setLatestData(getLatestData());
    }, [getLatestData]);

    const handleReset = React.useCallback(() => {
        setClickedData(null);
        onReset?.();
    }, [onReset]);

    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                handleReset();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleReset]);

    const displayData = clickedData || latestData;

    React.useEffect(() => {
        if (!svgRef.current) return;

        const margin = { top: 20, right: 150, bottom: 30, left: 60 };
        const width = 800 - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        const portfolioGroups = new Map<string, ChartLine[]>();

        activeData.forEach((portfolio, index) => {
            const color =
                portfolioColors[portfolio.portfolioId] ||
                PORTFOLIO_COLORS[index % PORTFOLIO_COLORS.length];

            const points: ChartLine[] = portfolio.performance.map((p) => ({
                date: new Date(p.date),
                value: p.value,
                portfolioId: portfolio.portfolioId,
                color,
            }));

            portfolioGroups.set(portfolio.portfolioId, points);
        });

        let benchmarkLines: ChartLine[] = [];
        if (selectedBenchmark && benchmarkData?.[selectedBenchmark]) {
            benchmarkLines = benchmarkData[selectedBenchmark].map((d) => ({
                date: new Date(d.date),
                value: d.price,
                ticker: selectedBenchmark,
            }));
        }

        const allLines: ChartLine[] = [];
        portfolioGroups.forEach((points) => {
            allLines.push(...points);
        });

        if (benchmarkLines.length > 0) {
            const benchmarkBase = benchmarkLines[0]?.value || 1;
            benchmarkLines = benchmarkLines.map((b) => ({
                ...b,
                value: ((b.value - benchmarkBase) / benchmarkBase) * 100,
            }));
        }

        const allValues = [...allLines.map((d) => d.value), ...benchmarkLines.map((d) => d.value)];

        if (allValues.length === 0) {
            g.append('text')
                .attr('x', width / 2)
                .attr('y', height / 2)
                .attr('text-anchor', 'middle')
                .attr('fill', '#94a3b8')
                .attr('font-size', '13px')
                .text('No agents selected. Select up to 5 agents above to compare.');
            return;
        }

        const x = d3.scaleTime().domain(dateRange).range([0, width]);

        const yMin = d3.min(allValues, (d) => d) ?? -10;
        const yMax = d3.max(allValues, (d) => d) ?? 10;
        const yPadding = Math.max((yMax - yMin) * 0.1, 1);

        const y = d3
            .scaleLinear()
            .domain([yMin - yPadding, yMax + yPadding])
            .nice()
            .range([height, 0]);

        g.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x).ticks(5))
            .attr('color', '#94a3b8');

        g.append('g')
            .call(
                d3
                    .axisLeft(y)
                    .tickFormat((d) => `${Number(d) > 0 ? '+' : ''}${Number(d).toFixed(1)}%`),
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

        g.append('line')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', y(0))
            .attr('y2', y(0))
            .attr('stroke', '#a1a1aa')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '4,4');

        const line = d3
            .line<ChartLine>()
            .defined(
                (d) =>
                    d.date instanceof Date &&
                    !Number.isNaN(d.date.getTime()) &&
                    !Number.isNaN(d.value),
            )
            .x((d) => x(d.date))
            .y((d) => y(d.value))
            .curve(d3.curveMonotoneX);

        portfolioGroups.forEach((points, portfolioId) => {
            const sorted = [...points].sort((a, b) => a.date.getTime() - b.date.getTime());
            const color = portfolioColors[portfolioId];

            g.append('path')
                .datum(sorted)
                .attr('class', `portfolio-line portfolio-line-${portfolioId}`)
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 2.5)
                .attr('opacity', 0)
                .attr('d', line)
                .transition()
                .duration(350)
                .ease(d3.easeQuadInOut)
                .attr('opacity', 1);
        });

        if (benchmarkLines.length > 0) {
            const sortedBenchmark = [...benchmarkLines].sort(
                (a, b) => a.date.getTime() - b.date.getTime(),
            );

            g.append('path')
                .datum(sortedBenchmark)
                .attr('class', 'benchmark-line')
                .attr('fill', 'none')
                .attr('stroke', '#f59e0b')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '6,3')
                .attr('opacity', 0)
                .attr('d', line)
                .transition()
                .duration(350)
                .ease(d3.easeQuadInOut)
                .attr('opacity', 1);
        }

        const bisector = d3.bisector<ChartLine, Date>((d) => d.date).left;

        const _overlay = g
            .append('rect')
            .attr('class', 'overlay')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', 'none')
            .attr('pointer-events', 'all')
            .attr('cursor', 'crosshair')
            .on('click', (event) => {
                const [mouseX] = d3.pointer(event);
                const x0 = x.invert(mouseX);

                const portfolioValues: {
                    ownerId: string;
                    value: number;
                    color: string;
                    date: Date;
                }[] = [];
                let tooltipDate: Date | undefined;

                portfolioGroups.forEach((points, portfolioId) => {
                    const sorted = [...points].sort((a, b) => a.date.getTime() - b.date.getTime());
                    const x0Idx = bisector(sorted, x0, 1);
                    const d0 = sorted[x0Idx - 1];
                    const d1 = sorted[x0Idx];
                    const pt =
                        d0 && d1 ? (mouseX - x(d0.date) < x(d1.date) - mouseX ? d0 : d1) : d0 || d1;

                    if (pt) {
                        if (!tooltipDate) tooltipDate = pt.date;
                        const portfolio = activeData.find((p) => p.portfolioId === portfolioId);
                        portfolioValues.push({
                            ownerId: portfolio?.ownerId || portfolioId,
                            value: pt.value,
                            color: portfolioColors[portfolioId],
                            date: pt.date,
                        });
                    }
                });

                let benchmarkPt: ChartLine | undefined;
                if (benchmarkLines.length > 0) {
                    const sortedBenchmark = [...benchmarkLines].sort(
                        (a, b) => a.date.getTime() - b.date.getTime(),
                    );
                    const bX0 = bisector(sortedBenchmark, x0, 1);
                    const bD0 = sortedBenchmark[bX0 - 1];
                    const bD1 = sortedBenchmark[bX0];
                    benchmarkPt =
                        bD0 && bD1
                            ? mouseX - x(bD0.date) < x(bD1.date) - mouseX
                                ? bD0
                                : bD1
                            : bD0 || bD1;
                }

                if (portfolioValues.length > 0 && tooltipDate) {
                    const firstPt = portfolioValues[0];
                    setClickedData({
                        date: tooltipDate.toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                        }),
                        portfolioValues,
                        benchmarkValue: benchmarkPt?.value,
                        benchmarkTicker: benchmarkPt?.ticker,
                        x: x(tooltipDate),
                        y: y(firstPt.value),
                    });
                }
            });

        g.append('line')
            .attr('class', 'crosshair')
            .attr('stroke', '#64748b')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '4,4')
            .attr('opacity', 0)
            .attr('x1', 0)
            .attr('x2', 0)
            .attr('y1', 0)
            .attr('y2', height);

        portfolioGroups.forEach((_points, portfolioId) => {
            const color = portfolioColors[portfolioId];
            g.append('circle')
                .attr('class', `dot-${portfolioId}`)
                .attr('r', 5)
                .attr('fill', color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 2)
                .attr('opacity', 0);
        });

        g.append('circle')
            .attr('class', 'benchmark-dot')
            .attr('r', 5)
            .attr('fill', '#f59e0b')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .attr('opacity', 0);

        const legend = g.append('g').attr('transform', `translate(${width + 20}, 20)`);

        let legendY = 0;
        portfolioGroups.forEach((_points, portfolioId) => {
            const portfolio = activeData.find((p) => p.portfolioId === portfolioId);
            const color = portfolioColors[portfolioId];
            const label = portfolio?.ownerId.replace(/-/g, ' ') || portfolioId;

            legend
                .append('line')
                .attr('x1', 0)
                .attr('x2', 16)
                .attr('y1', legendY)
                .attr('y2', legendY)
                .attr('stroke', color)
                .attr('stroke-width', 2.5);

            legend
                .append('text')
                .attr('x', 24)
                .attr('y', legendY + 4)
                .attr('font-size', '11px')
                .attr('fill', '#64748b')
                .text(label);

            legendY += 22;
        });

        if (benchmarkLines.length > 0) {
            legend
                .append('line')
                .attr('x1', 0)
                .attr('x2', 16)
                .attr('y1', legendY + 2)
                .attr('y2', legendY + 2)
                .attr('stroke', '#f59e0b')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '6,3');

            const benchmarkLabel =
                BENCHMARK_OPTIONS.find((b) => b.ticker === selectedBenchmark)?.label ||
                selectedBenchmark;
            legend
                .append('text')
                .attr('x', 24)
                .attr('y', legendY + 6)
                .attr('font-size', '11px')
                .attr('fill', '#f59e0b')
                .text(benchmarkLabel);
        }
    }, [activeData, portfolioColors, benchmarkData, selectedBenchmark, dateRange]);

    React.useEffect(() => {
        if (!svgRef.current) return;

        const svg = d3.select(svgRef.current);
        const margin = { top: 20, right: 150, bottom: 30, left: 60 };
        const width = 800 - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;

        const x = d3.scaleTime().domain(dateRange).range([0, width]);

        const allValues = activeData.flatMap((p) => p.performance.map((pp) => pp.value));
        const yMin = d3.min(allValues, (d) => d) ?? -10;
        const yMax = d3.max(allValues, (d) => d) ?? 10;
        const yPadding = Math.max((yMax - yMin) * 0.1, 1);
        const y = d3
            .scaleLinear()
            .domain([yMin - yPadding, yMax + yPadding])
            .nice()
            .range([height, 0]);

        if (!displayData) return;

        if (clickedData) {
            svg.select('.crosshair')
                .attr('opacity', 1)
                .attr('transform', `translate(${clickedData.x},0)`);

            activeData.forEach((portfolio) => {
                const dot = svg.select(`.dot-${portfolio.portfolioId}`);
                const pv = clickedData.portfolioValues.find((p) => p.ownerId === portfolio.ownerId);
                if (dot.size() > 0 && pv) {
                    dot.attr('opacity', 1).attr('cx', clickedData.x).attr('cy', y(pv.value));
                }
            });

            if (clickedData.benchmarkValue !== undefined) {
                svg.select('.benchmark-dot')
                    .attr('opacity', 1)
                    .attr('cx', clickedData.x)
                    .attr('cy', y(clickedData.benchmarkValue));
            }
        } else {
            const latest = latestData;
            if (latest && activeData.length > 0) {
                const lastDate = new Date(latest.date || Date.now());
                const _xPos = x(lastDate);

                svg.select('.crosshair').attr('opacity', 0);

                activeData.forEach((portfolio, _index) => {
                    const dot = svg.select(`.dot-${portfolio.portfolioId}`);
                    const pv = latest.portfolioValues.find((p) => p.ownerId === portfolio.ownerId);
                    if (dot.size() > 0 && pv) {
                        dot.attr('opacity', 0);
                    }
                });

                svg.select('.benchmark-dot').attr('opacity', 0);
            }
        }
    }, [clickedData, latestData, displayData, activeData, dateRange]);

    const sortedPortfolioValues = displayData?.portfolioValues
        ? [...displayData.portfolioValues].sort((a, b) => b.value - a.value)
        : [];

    return (
        <div className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 shadow-sm overflow-hidden flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-wider">
                    Performance Comparison
                </h3>
                <div className="flex items-center gap-3">
                    <div className="text-xs text-zinc-400">Normalized to percentage returns</div>
                    {clickedData && (
                        <Button variant="ghost" colorScheme="info" size="sm" onClick={handleReset}>
                            Reset Crosshair
                        </Button>
                    )}
                </div>
            </div>

            {data.length > 0 && (
                <PortfolioComparisonSelector
                    availablePortfolios={data.map((p) => ({
                        portfolioId: p.portfolioId,
                        ownerId: p.ownerId,
                    }))}
                    selectedIds={selectedPortfolioIds}
                    portfolioColors={portfolioColors}
                    onAdd={handleAddPortfolio}
                    onRemove={handleRemovePortfolio}
                    onReset={isCustomSelection ? handleResetSelection : undefined}
                    maxSelected={maxSelected}
                />
            )}

            {displayData && sortedPortfolioValues.length > 0 && (
                <div className="p-3 bg-zinc-50 dark:bg-zinc-800/40 rounded-lg border border-zinc-100 dark:border-zinc-800">
                    <div className="text-xs text-zinc-500 mb-2">{displayData.date}</div>
                    <div className="space-y-1">
                        {sortedPortfolioValues.map((pv) => (
                            <div
                                key={pv.ownerId}
                                className="flex items-center justify-between gap-4 text-sm"
                            >
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-2 h-2 rounded-full shrink-0"
                                        style={{ backgroundColor: pv.color }}
                                    />
                                    <span className="text-zinc-600 dark:text-zinc-300 capitalize truncate max-w-xs">
                                        {pv.ownerId.replace(/-/g, ' ')}
                                    </span>
                                </div>
                                <span
                                    className={`font-semibold ${
                                        pv.value >= 0 ? 'text-emerald-600' : 'text-red-600'
                                    }`}
                                >
                                    {pv.value >= 0 ? '+' : ''}
                                    {pv.value.toFixed(2)}%
                                </span>
                            </div>
                        ))}
                        {displayData.benchmarkValue !== undefined && (
                            <div className="flex items-center justify-between gap-4 text-sm pt-2 border-t border-zinc-200 dark:border-zinc-700">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                                    <span className="text-amber-600">
                                        {BENCHMARK_OPTIONS.find(
                                            (b) => b.ticker === selectedBenchmark,
                                        )?.label || selectedBenchmark}
                                    </span>
                                </div>
                                <span
                                    className={`font-semibold ${
                                        displayData.benchmarkValue >= 0
                                            ? 'text-emerald-600'
                                            : 'text-red-600'
                                    }`}
                                >
                                    {displayData.benchmarkValue >= 0 ? '+' : ''}
                                    {displayData.benchmarkValue.toFixed(2)}%
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            )}
            <div className="w-full overflow-x-auto relative">
                <svg
                    ref={svgRef}
                    data-testid="portfolio-comparison-svg"
                    width="100%"
                    height="400"
                    viewBox="0 0 800 400"
                    preserveAspectRatio="xMidYMid meet"
                    style={{ transition: 'opacity 150ms ease' }}
                />
            </div>
            <div className="text-xs text-zinc-400 text-center">
                Click on chart to see performance at a specific date · Press Esc to reset
            </div>
        </div>
    );
}
