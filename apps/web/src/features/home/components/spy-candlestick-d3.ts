import * as d3 from 'd3';
import type { CandlestickBar, ChartTradeMarker } from './SPYCandlestickChart';

export function drawGridAndAxes(
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

export function drawVolumeBars(
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

export function drawCandlesticks(
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

interface BarTimestamp {
    bar: CandlestickBar;
    timeMs: number;
}

function findBarByTimestamp(tradeMs: number, barTimeList: BarTimestamp[]): CandlestickBar | null {
    if (Number.isNaN(tradeMs)) return null;

    for (const item of barTimeList) {
        if (
            !Number.isNaN(item.timeMs) &&
            tradeMs >= item.timeMs &&
            tradeMs < item.timeMs + 60_000
        ) {
            return item.bar;
        }
    }

    let closestBar: CandlestickBar | null = null;
    let minDiff = 60_000;
    for (const item of barTimeList) {
        if (!Number.isNaN(item.timeMs)) {
            const diff = Math.abs(tradeMs - item.timeMs);
            if (diff < minDiff) {
                minDiff = diff;
                closestBar = item.bar;
            }
        }
    }
    return closestBar;
}

export function matchTradesToBars(
    trades: ChartTradeMarker[],
    bars: CandlestickBar[],
): Map<string, ChartTradeMarker[]> {
    const map = new Map<string, ChartTradeMarker[]>();
    if (!bars.length || !trades.length) return map;

    const barTimeList: BarTimestamp[] = bars.map((b) => ({
        bar: b,
        timeMs: new Date(b.time).getTime(),
    }));

    for (const trade of trades) {
        const exact = bars.find((b) => b.time === trade.time);
        const matched = exact ?? findBarByTimestamp(new Date(trade.time).getTime(), barTimeList);

        if (matched) {
            const existing = map.get(matched.time) ?? [];
            existing.push(trade);
            map.set(matched.time, existing);
        }
    }

    return map;
}

function renderMarkerTriangle(
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    trade: ChartTradeMarker,
    candleX: number,
    candleY: number,
    isSelected: boolean,
    onToggleTrade: (trade: ChartTradeMarker) => void,
) {
    const isBuy = trade.action === 'BUY';
    const markerGroup = g
        .append('g')
        .datum(trade)
        .attr('class', `trade-marker${isSelected ? ' is-selected' : ''}`)
        .attr('transform', `translate(${candleX}, ${candleY})`)
        .attr('role', 'button')
        .attr('tabindex', 0)
        .attr(
            'aria-label',
            `${trade.action} trade at $${trade.price.toFixed(2)}${trade.shares ? ` for ${trade.shares} shares` : ''}`,
        )
        .style('cursor', 'pointer')
        .on('click', (event) => {
            event.stopPropagation();
            onToggleTrade(trade);
        })
        .on('keydown', (event: KeyboardEvent) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                event.stopPropagation();
                onToggleTrade(trade);
            }
        });

    // 24x24 hit target to ensure accessible click/touch target size (WCAG 2.5.5)
    markerGroup
        .append('rect')
        .attr('x', -12)
        .attr('y', -12)
        .attr('width', 24)
        .attr('height', 24)
        .attr('fill', 'transparent');

    const trianglePath = isBuy
        ? isSelected
            ? 'M -7,10 L 7,10 L 0,-2 Z'
            : 'M -5,8 L 5,8 L 0,-1 Z'
        : isSelected
          ? 'M -7,-10 L 7,-10 L 0,2 Z'
          : 'M -5,-8 L 5,-8 L 0,1 Z';

    markerGroup
        .append('path')
        .attr('d', trianglePath)
        .attr('fill', isBuy ? '#68d391' : '#e56b55')
        .attr('stroke', isSelected ? '#f59e0b' : '#101713')
        .attr('stroke-width', isSelected ? 2.5 : 1.5);
}

export function updateMarkerSelection(
    el: d3.Selection<SVGGElement, unknown, null, undefined>,
    markerTrade: ChartTradeMarker,
    selectedTrade: ChartTradeMarker | null,
) {
    const isSelected =
        selectedTrade !== null &&
        (selectedTrade.id && markerTrade.id
            ? selectedTrade.id === markerTrade.id
            : selectedTrade.time === markerTrade.time &&
              selectedTrade.action === markerTrade.action &&
              selectedTrade.price === markerTrade.price);

    el.classed('is-selected', isSelected);
    const isBuy = markerTrade.action === 'BUY';
    const trianglePath = isBuy
        ? isSelected
            ? 'M -7,10 L 7,10 L 0,-2 Z'
            : 'M -5,8 L 5,8 L 0,-1 Z'
        : isSelected
          ? 'M -7,-10 L 7,-10 L 0,2 Z'
          : 'M -5,-8 L 5,-8 L 0,1 Z';

    el.select('path')
        .attr('d', trianglePath)
        .attr('stroke', isSelected ? '#f59e0b' : '#101713')
        .attr('stroke-width', isSelected ? 2.5 : 1.5);
}

export function drawTradeMarkers(
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    trades: ChartTradeMarker[],
    bars: CandlestickBar[],
    xScale: d3.ScaleBand<string>,
    yScale: d3.ScaleLinear<number, number>,
    plotHeight: number,
    volumeHeight: number,
    onToggleTrade: (trade: ChartTradeMarker) => void,
) {
    const tradesByBar = matchTradesToBars(trades, bars);
    const minY = 14;
    const maxY = Math.max(minY, plotHeight - volumeHeight - 14);

    for (const [barTime, barTrades] of tradesByBar.entries()) {
        const xPos = xScale(barTime);
        if (xPos === undefined) continue;

        const matchingBar = bars.find((b) => b.time === barTime);
        if (!matchingBar) continue;

        const candleCenterX = xPos + xScale.bandwidth() / 2;
        const count = barTrades.length;

        barTrades.forEach((trade, index) => {
            let candleX = candleCenterX;
            if (count > 1) {
                const maxSpread = Math.min(xScale.bandwidth() * 0.7, (count - 1) * 12);
                const step = maxSpread / (count - 1);
                candleX = candleCenterX - maxSpread / 2 + index * step;
            }

            const isBuy = trade.action === 'BUY';
            const rawCandleY = isBuy ? yScale(matchingBar.low) + 12 : yScale(matchingBar.high) - 12;
            const candleY = Math.max(minY, Math.min(maxY, rawCandleY));

            renderMarkerTriangle(g, trade, candleX, candleY, false, onToggleTrade);
        });
    }
}
