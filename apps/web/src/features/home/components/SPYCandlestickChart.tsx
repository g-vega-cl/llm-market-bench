import * as d3 from 'd3';
import * as React from 'react';

export interface CandlestickBar {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export interface ChartTradeMarker {
    time: string;
    action: 'BUY' | 'SELL';
    price: number;
    shares?: number;
}

export interface SPYCandlestickChartProps {
    bars: CandlestickBar[];
    trades?: ChartTradeMarker[];
    height?: number;
    className?: string;
}

function drawGridAndAxes(
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    yScale: d3.ScaleLinear<number, number>,
    width: number,
) {
    const yTicks = yScale.ticks(5);
    g.append('g')
        .selectAll('line.grid-line')
        .data(yTicks)
        .enter()
        .append('line')
        .attr('class', 'grid-line')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('y1', (d) => yScale(d))
        .attr('y2', (d) => yScale(d))
        .attr('stroke', '#23322a')
        .attr('stroke-dasharray', '2,2')
        .attr('stroke-width', 1);

    const yAxis = d3
        .axisRight(yScale)
        .tickValues(yTicks)
        .tickFormat((d) => Number(d).toFixed(2));

    g.append('g')
        .attr('transform', `translate(${width}, 0)`)
        .call(yAxis)
        .call((sel) => sel.select('.domain').remove())
        .selectAll('text')
        .attr('fill', '#93a79d')
        .attr('font-size', '10px')
        .attr('font-family', 'ui-monospace, monospace');
}

function drawVolumeBars(
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    bars: CandlestickBar[],
    xScale: d3.ScaleBand<string>,
    yVolScale: d3.ScaleLinear<number, number>,
    plotHeight: number,
) {
    g.selectAll('rect.volume-bar')
        .data(bars)
        .enter()
        .append('rect')
        .attr('class', 'volume-bar')
        .attr('x', (d) => xScale(d.time) ?? 0)
        .attr('y', (d) => yVolScale(d.volume))
        .attr('width', xScale.bandwidth())
        .attr('height', (d) => plotHeight - yVolScale(d.volume))
        .attr('fill', (d) => (d.close >= d.open ? '#244837' : '#4a2825'))
        .attr('opacity', 0.6);
}

function drawCandlesticks(
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    bars: CandlestickBar[],
    xScale: d3.ScaleBand<string>,
    yScale: d3.ScaleLinear<number, number>,
    onHover: (b: CandlestickBar | null) => void,
) {
    g.selectAll('line.candlestick-wick')
        .data(bars)
        .enter()
        .append('line')
        .attr('class', 'candlestick-wick')
        .attr('x1', (d) => (xScale(d.time) ?? 0) + xScale.bandwidth() / 2)
        .attr('x2', (d) => (xScale(d.time) ?? 0) + xScale.bandwidth() / 2)
        .attr('y1', (d) => yScale(d.high))
        .attr('y2', (d) => yScale(d.low))
        .attr('stroke', (d) => (d.close >= d.open ? '#68d391' : '#e56b55'))
        .attr('stroke-width', 1.5);

    g.selectAll('rect.candlestick-body')
        .data(bars)
        .enter()
        .append('rect')
        .attr('class', 'candlestick-body')
        .attr('x', (d) => xScale(d.time) ?? 0)
        .attr('y', (d) => yScale(Math.max(d.open, d.close)))
        .attr('width', xScale.bandwidth())
        .attr('height', (d) => Math.max(3, Math.abs(yScale(d.open) - yScale(d.close))))
        .attr('fill', (d) => (d.close >= d.open ? '#68d391' : '#e56b55'))
        .attr('stroke', (d) => (d.close >= d.open ? '#48bb78' : '#c53030'))
        .attr('stroke-width', 1)
        .style('cursor', 'crosshair')
        .on('mouseenter', (_, d) => onHover(d))
        .on('mouseleave', () => onHover(null));
}

function drawTradeMarkers(
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    trades: ChartTradeMarker[],
    xScale: d3.ScaleBand<string>,
    yScale: d3.ScaleLinear<number, number>,
) {
    for (const trade of trades) {
        const xPos = xScale(trade.time);
        if (xPos === undefined) continue;
        const candleX = xPos + xScale.bandwidth() / 2;
        const candleY = yScale(trade.price);
        const isBuy = trade.action === 'BUY';

        const markerGroup = g
            .append('g')
            .attr('class', 'trade-marker')
            .attr('transform', `translate(${candleX}, ${candleY})`);

        const trianglePath = isBuy ? 'M -5,8 L 5,8 L 0,-1 Z' : 'M -5,-8 L 5,-8 L 0,1 Z';

        markerGroup
            .append('path')
            .attr('d', trianglePath)
            .attr('fill', isBuy ? '#68d391' : '#e56b55')
            .attr('stroke', '#101713')
            .attr('stroke-width', 1.5);

        markerGroup
            .append('title')
            .text(
                `${trade.action} @ $${trade.price.toFixed(2)}${trade.shares ? ` (${trade.shares} sh)` : ''}`,
            );
    }
}

interface ChartHeaderHUDProps {
    activeDisplay: CandlestickBar | null;
    priceChange: number;
    pctChange: number;
}

function ChartHeaderHUD({ activeDisplay, priceChange, pctChange }: ChartHeaderHUDProps) {
    const timeET = React.useMemo(() => {
        if (!activeDisplay?.time) return null;
        try {
            return new Date(activeDisplay.time).toLocaleTimeString('en-US', {
                timeZone: 'America/New_York',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false,
            });
        } catch {
            return null;
        }
    }, [activeDisplay?.time]);

    return (
        <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-xs font-mono">
            <div className="flex items-center gap-2.5">
                <span className="text-boxel-muted uppercase font-black tracking-wider bg-boxel-surface border border-boxel-border px-1.5 py-0.5">
                    SPY 1M
                </span>
                {activeDisplay && (
                    <span className="font-bold text-boxel-ink text-sm">
                        ${activeDisplay.close.toFixed(2)}
                    </span>
                )}
                <span className={`font-bold ${priceChange >= 0 ? 'text-success' : 'text-danger'}`}>
                    {priceChange >= 0 ? '+' : ''}
                    {priceChange.toFixed(2)} ({pctChange >= 0 ? '+' : ''}
                    {pctChange.toFixed(2)}%)
                </span>
            </div>
            {activeDisplay && (
                <div className="flex flex-wrap items-center gap-2.5 text-boxel-muted">
                    <span>
                        <strong className="text-boxel-ink font-bold">O:</strong> $
                        {activeDisplay.open.toFixed(2)}
                    </span>
                    <span>
                        <strong className="text-boxel-ink font-bold">H:</strong> $
                        {activeDisplay.high.toFixed(2)}
                    </span>
                    <span>
                        <strong className="text-boxel-ink font-bold">L:</strong> $
                        {activeDisplay.low.toFixed(2)}
                    </span>
                    <span>
                        <strong className="text-boxel-ink font-bold">C:</strong> $
                        {activeDisplay.close.toFixed(2)}
                    </span>
                    <span className="border-l border-boxel-border pl-2">
                        <strong className="text-boxel-ink font-bold">Vol:</strong>{' '}
                        {activeDisplay.volume.toLocaleString('en-US')}
                    </span>
                    {timeET && (
                        <span className="border-l border-boxel-border pl-2 text-[11px]">
                            {timeET} ET
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}

export function SPYCandlestickChart({
    bars: inputBars,
    trades = [],
    height = 380,
    className = '',
}: SPYCandlestickChartProps) {
    const bars = React.useMemo(() => (inputBars ? inputBars.slice(-60) : []), [inputBars]);
    const svgRef = React.useRef<SVGSVGElement>(null);
    const containerRef = React.useRef<HTMLDivElement>(null);
    const [containerWidth, setContainerWidth] = React.useState(600);
    const [hoveredBar, setHoveredBar] = React.useState<CandlestickBar | null>(null);

    React.useEffect(() => {
        if (!containerRef.current || typeof ResizeObserver === 'undefined') return;
        const observer = new ResizeObserver((entries) => {
            for (const entry of entries) {
                if (entry.contentRect.width > 0) {
                    setContainerWidth(entry.contentRect.width);
                }
            }
        });
        observer.observe(containerRef.current);
        return () => observer.disconnect();
    }, []);

    const lastBar = bars.length > 0 ? bars[bars.length - 1] : null;
    const firstBar = bars.length > 0 ? bars[0] : null;
    const priceChange =
        lastBar && firstBar ? Number((lastBar.close - firstBar.open).toFixed(2)) : 0;
    const pctChange =
        lastBar && firstBar && firstBar.open > 0
            ? Number(((priceChange / firstBar.open) * 100).toFixed(2))
            : 0;

    React.useEffect(() => {
        if (!svgRef.current || bars.length === 0) return;

        const margin = { top: 16, right: 60, bottom: 24, left: 12 };
        const width = Math.max(containerWidth, 240) - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        const volumeHeight = Math.floor(plotHeight * 0.2);
        const candleHeight = plotHeight - volumeHeight - 10;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        const xScale = d3
            .scaleBand<string>()
            .domain(bars.map((b) => b.time))
            .range([0, width])
            .padding(0.25);

        const minLow = d3.min(bars, (b) => b.low) ?? 760;
        const maxHigh = d3.max(bars, (b) => b.high) ?? 770;
        const pricePadding = (maxHigh - minLow) * 0.08 || 0.5;

        const yScale = d3
            .scaleLinear()
            .domain([minLow - pricePadding, maxHigh + pricePadding])
            .range([candleHeight, 0]);

        const maxVolume = d3.max(bars, (b) => b.volume) ?? 1;
        const yVolScale = d3
            .scaleLinear()
            .domain([0, maxVolume])
            .range([plotHeight, plotHeight - volumeHeight]);

        drawGridAndAxes(g, yScale, width);
        drawVolumeBars(g, bars, xScale, yVolScale, plotHeight);
        drawCandlesticks(g, bars, xScale, yScale, setHoveredBar);
        drawTradeMarkers(g, trades, xScale, yScale);
    }, [bars, trades, containerWidth, height]);

    if (bars.length === 0) {
        return (
            <div
                className={`voxel-trough flex items-center justify-center p-8 text-xs text-boxel-muted font-mono ${className}`}
            >
                Awaiting live SPY market tape...
            </div>
        );
    }

    const activeDisplay = hoveredBar || lastBar;

    return (
        <div ref={containerRef} className={`flex flex-col gap-2.5 w-full ${className}`}>
            <ChartHeaderHUD
                activeDisplay={activeDisplay}
                priceChange={priceChange}
                pctChange={pctChange}
            />
            <div className="voxel-trough overflow-hidden w-full relative">
                <svg ref={svgRef} width={containerWidth} height={height} className="block w-full" />
            </div>
        </div>
    );
}
