import * as d3 from 'd3';
import * as React from 'react';
import { formatEasternExactTime } from '~/utils/date';
import {
    drawCandlesticks,
    drawGridAndAxes,
    drawTradeMarkers,
    drawVolumeBars,
    updateMarkerSelection,
} from './spy-candlestick-d3';

export interface CandlestickBar {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export interface ChartTradeMarker {
    id?: string;
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
            <div className="flex items-center gap-2">
                <span className="text-boxel-muted uppercase font-bold tracking-wider bg-boxel-surface border border-boxel-border px-1.5 py-0.5">
                    SPY 1M
                </span>
                {activeDisplay ? (
                    <>
                        <span className="font-bold text-boxel-ink text-sm">
                            ${activeDisplay.close.toFixed(2)}
                        </span>
                        <span
                            className={`font-bold ${priceChange >= 0 ? 'text-success' : 'text-danger'}`}
                        >
                            {priceChange >= 0 ? '+' : ''}
                            {priceChange.toFixed(2)} ({pctChange >= 0 ? '+' : ''}
                            {pctChange.toFixed(2)}%)
                        </span>
                    </>
                ) : (
                    <span className="text-boxel-muted">Syncing market tape...</span>
                )}
            </div>
            {activeDisplay && (
                <div className="flex flex-wrap items-center gap-2 text-boxel-muted">
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
                        <span className="border-l border-boxel-border pl-2 text-xs font-normal">
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
    const [selectedTrade, setSelectedTrade] = React.useState<ChartTradeMarker | null>(null);

    const handleToggleTrade = React.useCallback((trade: ChartTradeMarker) => {
        setSelectedTrade((prev) => {
            const isMatch =
                prev !== null &&
                (prev.id && trade.id
                    ? prev.id === trade.id
                    : prev.time === trade.time &&
                      prev.action === trade.action &&
                      prev.price === trade.price);
            return isMatch ? null : trade;
        });
    }, []);

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

    // Primary chart rendering effect (isolated from selection state to prevent canvas teardown)
    React.useEffect(() => {
        if (!svgRef.current) return;

        const margin = { top: 16, right: 60, bottom: 24, left: 12 };
        const width = Math.max(containerWidth, 240) - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        const volumeHeight = Math.floor(plotHeight * 0.2);
        const candleHeight = plotHeight - volumeHeight - 10;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();
        svg.on('click', () => setSelectedTrade(null));

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        if (bars.length === 0) {
            const emptyYScale = d3.scaleLinear().domain([580, 585]).range([candleHeight, 0]);
            drawGridAndAxes(g, emptyYScale, width);
            g.append('text')
                .attr('class', 'chart-empty-message')
                .attr('x', width / 2)
                .attr('y', candleHeight / 2)
                .attr('text-anchor', 'middle')
                .attr('fill', '#93a79d')
                .attr('font-size', '12px')
                .attr('font-family', 'ui-monospace, monospace')
                .text('Awaiting live SPY market tape...');
            return;
        }

        const xScale = d3
            .scaleBand<string>()
            .domain(bars.map((b) => b.time))
            .range([0, width])
            .padding(0.25);

        const minLow = d3.min(bars, (b) => b.low) ?? 760;
        const maxHigh = d3.max(bars, (b) => b.high) ?? 770;
        const pricePadding = (maxHigh - minLow) * 0.12 || 0.8;

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
        drawTradeMarkers(
            g,
            trades,
            bars,
            xScale,
            yScale,
            plotHeight,
            volumeHeight,
            handleToggleTrade,
        );
    }, [bars, trades, containerWidth, height, handleToggleTrade]);

    // Fast selection-state toggle effect (preserves SVG DOM without redrawing grid/axes/candles)
    React.useEffect(() => {
        if (!svgRef.current) return;
        const svg = d3.select(svgRef.current);
        svg.selectAll<SVGGElement, unknown>('.trade-marker').each(function () {
            const el = d3.select(this);
            const markerTrade = el.datum() as ChartTradeMarker | undefined;
            if (markerTrade) {
                updateMarkerSelection(el, markerTrade, selectedTrade);
            }
        });
    }, [selectedTrade]);

    const activeDisplay = hoveredBar || lastBar;
    const selectedTradeTimeET = React.useMemo(
        () => (selectedTrade?.time ? formatEasternExactTime(selectedTrade.time) : null),
        [selectedTrade?.time],
    );

    return (
        <div ref={containerRef} className={`flex flex-col gap-2 w-full ${className}`}>
            <ChartHeaderHUD
                activeDisplay={activeDisplay}
                priceChange={priceChange}
                pctChange={pctChange}
            />
            <div className="voxel-trough overflow-hidden w-full relative">
                <svg ref={svgRef} width={containerWidth} height={height} className="block w-full" />
            </div>
            {selectedTrade && (
                <div
                    data-testid="selected-trade-slot"
                    className="voxel-trough p-2 flex flex-wrap items-center justify-between gap-2 text-xs font-mono border border-boxel-border"
                >
                    <div className="flex flex-wrap items-center gap-2 min-w-0">
                        <span
                            className={`font-bold px-1.5 py-0.5 text-xs ${
                                selectedTrade.action === 'BUY'
                                    ? 'text-success bg-boxel-surface border border-success/40'
                                    : 'text-danger bg-boxel-surface border border-danger/40'
                            }`}
                        >
                            {selectedTrade.action}
                        </span>
                        {selectedTrade.shares !== undefined && (
                            <span className="text-boxel-ink whitespace-nowrap">
                                <strong className="text-boxel-muted font-bold">QTY:</strong>{' '}
                                {selectedTrade.shares} sh
                            </span>
                        )}
                        <span className="text-boxel-ink whitespace-nowrap">
                            <strong className="text-boxel-muted font-bold">PRICE:</strong> $
                            {selectedTrade.price.toFixed(2)}
                        </span>
                        {selectedTrade.shares !== undefined && (
                            <span className="text-boxel-ink whitespace-nowrap">
                                <strong className="text-boxel-muted font-bold">TOTAL:</strong> $
                                {(selectedTrade.shares * selectedTrade.price).toLocaleString(
                                    'en-US',
                                    {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2,
                                    },
                                )}
                            </span>
                        )}
                        {selectedTradeTimeET && (
                            <span className="border-l border-boxel-border pl-2 text-boxel-muted whitespace-nowrap">
                                {selectedTradeTimeET}
                            </span>
                        )}
                    </div>
                    <button
                        type="button"
                        aria-label="Close trade details"
                        onClick={() => setSelectedTrade(null)}
                        className="voxel-btn text-xs px-2 py-0.5 text-boxel-muted hover:text-boxel-ink cursor-pointer"
                    >
                        ✕
                    </button>
                </div>
            )}
        </div>
    );
}
