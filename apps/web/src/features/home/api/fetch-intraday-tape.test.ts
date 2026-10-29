import { describe, expect, it } from 'vitest';
import { generateFallbackIntradayBars, isRegularMarketHours } from './fetch-intraday-tape';

describe('fetch-intraday-tape utilities', () => {
    it('generates expected count of candlestick bars with positive volumes', () => {
        const bars = generateFallbackIntradayBars(60, 580);
        expect(bars).toHaveLength(60);
        expect(bars[0].open).toBe(580);
        for (const b of bars) {
            expect(b.high).toBeGreaterThanOrEqual(b.low);
            expect(b.volume).toBeGreaterThan(0);
            expect(new Date(b.time).getTime()).toBeGreaterThan(0);
        }
    });

    it('identifies market hours correctly', () => {
        // Wednesday 15:00 UTC (11:00 AM ET) -> open
        const openTime = new Date('2026-10-28T15:00:00Z');
        expect(isRegularMarketHours(openTime)).toBe(true);

        // Saturday 15:00 UTC -> closed
        const weekendTime = new Date('2026-10-31T15:00:00Z');
        expect(isRegularMarketHours(weekendTime)).toBe(false);

        // Wednesday 02:00 UTC -> closed
        const nightTime = new Date('2026-10-28T02:00:00Z');
        expect(isRegularMarketHours(nightTime)).toBe(false);
    });
});
