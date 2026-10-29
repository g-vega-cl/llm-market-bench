import { describe, expect, it } from 'vitest';
import type { CandlestickBar } from '../components/SPYCandlestickChart';
import { filterLastBars, isRegularMarketHours } from './fetch-intraday-tape';

describe('fetch-intraday-tape utilities', () => {
    it('filters strictly the last maxBars items', () => {
        const dummyBars: CandlestickBar[] = Array.from({ length: 80 }, (_, i) => ({
            time: `2026-10-29T15:${i.toString().padStart(2, '0')}:00Z`,
            open: 767.0 + i * 0.05,
            high: 767.5 + i * 0.05,
            low: 766.8 + i * 0.05,
            close: 767.2 + i * 0.05,
            volume: 1000 + i * 50,
        }));

        const filtered = filterLastBars(dummyBars, 60);
        expect(filtered).toHaveLength(60);
        expect(filtered[filtered.length - 1].close).toBe(dummyBars[dummyBars.length - 1].close);
    });

    it('returns empty array when bars is null or empty', () => {
        expect(filterLastBars(null)).toEqual([]);
        expect(filterLastBars(undefined)).toEqual([]);
        expect(filterLastBars([])).toEqual([]);
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
