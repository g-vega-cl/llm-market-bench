import { describe, expect, it } from 'vitest';
import type { CandlestickBar, ChartTradeMarker } from './SPYCandlestickChart';
import { matchTradesToBars } from './spy-candlestick-d3';

describe('spy-candlestick-d3 matchTradesToBars', () => {
    const bars: CandlestickBar[] = [
        {
            time: '2026-10-29T14:00:00Z',
            open: 580.0,
            high: 581.0,
            low: 579.0,
            close: 580.5,
            volume: 1000,
        },
        {
            time: '2026-10-29T14:01:00Z',
            open: 580.5,
            high: 582.0,
            low: 580.0,
            close: 581.5,
            volume: 1200,
        },
    ];

    it('returns empty map when bars or trades are empty', () => {
        expect(matchTradesToBars([], bars).size).toBe(0);
        expect(
            matchTradesToBars([{ time: '2026-10-29T14:00:00Z', action: 'BUY', price: 580 }], [])
                .size,
        ).toBe(0);
    });

    it('matches trade with exact bar timestamp', () => {
        const trade: ChartTradeMarker = {
            time: '2026-10-29T14:00:00Z',
            action: 'BUY',
            price: 580.2,
        };
        const map = matchTradesToBars([trade], bars);
        expect(map.get('2026-10-29T14:00:00Z')).toHaveLength(1);
    });

    it('matches trade with sub-minute seconds into the 1-minute window', () => {
        const trade: ChartTradeMarker = {
            time: '2026-10-29T14:01:45.123Z',
            action: 'SELL',
            price: 581.8,
        };
        const map = matchTradesToBars([trade], bars);
        expect(map.get('2026-10-29T14:01:00Z')).toHaveLength(1);
    });

    it('groups multiple trades on the same candle bar', () => {
        const trades: ChartTradeMarker[] = [
            { time: '2026-10-29T14:00:10Z', action: 'BUY', price: 580.1 },
            { time: '2026-10-29T14:00:40Z', action: 'BUY', price: 580.4 },
        ];
        const map = matchTradesToBars(trades, bars);
        expect(map.get('2026-10-29T14:00:00Z')).toHaveLength(2);
    });
});
