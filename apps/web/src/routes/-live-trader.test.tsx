import { describe, expect, it } from 'vitest';
import { calculateBenchmarkMoves, Route } from './live-trader';

const historicalData = [
    { date: '2026-11-03', price: 754.35 },
    { date: '2026-11-04', price: 766.81 },
    { date: '2026-11-05', price: 733.0 },
    { date: '2026-11-06', price: 735.29 },
    { date: '2026-11-09', price: 752.69 },
];

describe('Live Trader route', () => {
    it('exposes a loader and a component now that it lives under /live-trader', () => {
        expect(Route.options.loader).toBeTypeOf('function');
        expect(Route.options.component).toBeTypeOf('function');
    });
});

describe('calculateBenchmarkMoves', () => {
    it('calculates moves purely from history when no live quote is provided', () => {
        const moves = calculateBenchmarkMoves(historicalData);
        expect(moves.todayPct).toBe(2.37);
        expect(moves.weekPct).toBe(-0.22);
    });

    it('incorporates today live intraday quote vs yesterday EOD close', () => {
        const moves = calculateBenchmarkMoves(historicalData, {
            price: 747.08,
            date: '2026-11-10',
        });
        expect(moves.todayPct).toBe(-0.75);
        expect(moves.weekPct).toBe(-0.96);
    });

    it('updates a same-day bar while the market is open', () => {
        const dataWithToday = [...historicalData, { date: '2026-11-10', price: 750.0 }];
        const moves = calculateBenchmarkMoves(
            dataWithToday,
            { price: 747.08, date: '2026-11-10' },
            true,
        );
        expect(moves.todayPct).toBe(-0.75);
    });

    it('preserves the official EOD close when the market is closed', () => {
        const dataWithEOD = [...historicalData, { date: '2026-11-10', price: 750.0 }];
        const moves = calculateBenchmarkMoves(
            dataWithEOD,
            { price: 747.08, date: '2026-11-10' },
            false,
        );
        expect(moves.todayPct).toBe(-0.36);
    });

    it('ignores a quote older than the latest benchmark bar', () => {
        const moves = calculateBenchmarkMoves(historicalData, {
            price: 700.0,
            date: '2026-11-05',
        });
        expect(moves.todayPct).toBe(2.37);
        expect(moves.weekPct).toBe(-0.22);
    });

    it('handles insufficient data gracefully', () => {
        expect(calculateBenchmarkMoves([])).toEqual({ todayPct: 0, weekPct: 0 });
        expect(calculateBenchmarkMoves([{ date: '2026-11-10', price: 747.08 }])).toEqual({
            todayPct: 0,
            weekPct: 0,
        });
    });
});
