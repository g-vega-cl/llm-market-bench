import { describe, expect, it } from 'vitest';
import type { HistoricalPricePoint } from './macro-tickers';
import { calculateMacroStats } from './macro-tickers';

describe('calculateMacroStats', () => {
    it('returns default fallback when history is missing or insufficient', () => {
        const result = calculateMacroStats('SPY', 'S&P 500', 'Equities', 500, []);
        expect(result.hasHistory).toBe(false);
        expect(result.price).toBe(500);
        expect(result.todayPctChange).toBe(0);
        expect(result.stdevPct).toBe(0);
        expect(result.regimeFlag).toBe('Normal');
    });

    it('calculates normal price changes and standard deviations when market is open', () => {
        // High volatility historical background (daily swings of ~2%):
        // Returns list will be: -2.94%, +3.03%, -2.91%, +3.00%
        // Standard deviation of returns will be around 3.2%
        // Today's move is: (100.5 - 100)/100 = +0.50% (well within 1.0 * stdev)
        const history: HistoricalPricePoint[] = [
            { price: 100, fetched_at: '2026-05-26T16:00:00Z' },
            { price: 103, fetched_at: '2026-05-25T16:00:00Z' },
            { price: 100, fetched_at: '2026-05-24T16:00:00Z' },
            { price: 103, fetched_at: '2026-05-23T16:00:00Z' },
            { price: 100, fetched_at: '2026-05-22T16:00:00Z' },
        ];

        const result = calculateMacroStats('SPY', 'S&P 500', 'Equities', 100.5, history);

        expect(result.hasHistory).toBe(true);
        expect(result.price).toBe(100.5);
        expect(result.todayPctChange).toBeCloseTo(0.5, 2);
        expect(result.stdevPct).toBeGreaterThan(2);
        expect(result.regimeFlag).toBe('Normal');
    });

    it('calculates stats using closed market logic when currentPrice matches history[0]', () => {
        const history: HistoricalPricePoint[] = [
            { price: 100, fetched_at: '2026-05-26T16:00:00Z' },
            { price: 98, fetched_at: '2026-05-25T16:00:00Z' },
            { price: 96, fetched_at: '2026-05-24T16:00:00Z' },
            { price: 94, fetched_at: '2026-05-23T16:00:00Z' },
        ];

        const result = calculateMacroStats('SPY', 'S&P 500', 'Equities', 100, history);

        expect(result.hasHistory).toBe(true);
        expect(result.price).toBe(100);
        expect(result.todayPctChange).toBeCloseTo(2.04, 2);
    });

    it('flags HIGHLY UNUSUAL movements when move is greater than 2 * stdev', () => {
        // Background returns are tiny (0.1% changes) -> stdev is ~0.11%
        // Today's move is 1.0% -> >2 * stdev
        const history: HistoricalPricePoint[] = [
            { price: 100.1, fetched_at: '2026-05-26T16:00:00Z' },
            { price: 100.0, fetched_at: '2026-05-25T16:00:00Z' },
            { price: 100.1, fetched_at: '2026-05-24T16:00:00Z' },
            { price: 100.0, fetched_at: '2026-05-23T16:00:00Z' },
            { price: 100.1, fetched_at: '2026-05-22T16:00:00Z' },
        ];

        const result = calculateMacroStats('SPY', 'S&P 500', 'Equities', 101.1, history);

        expect(result.hasHistory).toBe(true);
        expect(result.todayPctChange).toBeCloseTo(1.0, 2);
        expect(result.regimeFlag).toBe('⚠️ HIGHLY UNUSUAL');
    });

    it('flags UNUSUAL movements when move is greater than 1.5 * stdev but less than 2 * stdev', () => {
        // Background returns:
        // history[0]=100, history[1]=99, history[2]=100, history[3]=99, history[4]=100
        // returns: +1.01%, -1.00%, +1.01%, -1.00%
        // Mean return ~0%
        // Stdev return ~1.16%
        // todayPctChange = (102.1 - 100)/100 = 2.1%
        // 1.5 * stdev = 1.74%
        // 2.0 * stdev = 2.32%
        // Today's move (2.1%) is between 1.74% and 2.32%, yielding exactly ❗ UNUSUAL
        const history: HistoricalPricePoint[] = [
            { price: 100, fetched_at: '2026-05-26T16:00:00Z' },
            { price: 99, fetched_at: '2026-05-25T16:00:00Z' },
            { price: 100, fetched_at: '2026-05-24T16:00:00Z' },
            { price: 99, fetched_at: '2026-05-23T16:00:00Z' },
            { price: 100, fetched_at: '2026-05-22T16:00:00Z' },
        ];

        const result = calculateMacroStats('SPY', 'S&P 500', 'Equities', 102.1, history);

        expect(result.hasHistory).toBe(true);
        expect(result.regimeFlag).toBe('❗ UNUSUAL');
    });
});

describe('MACRO_TICKERS config', () => {
    it('includes a balanced mix of key indicators in Market default view', async () => {
        const { MACRO_TICKERS } = await import('./macro-tickers');
        const marketTickers = Object.keys(MACRO_TICKERS.Market);

        // Equity
        expect(marketTickers).toContain('SPY');
        expect(marketTickers).toContain('QQQ');
        // Bond Yields
        expect(marketTickers).toContain('TLT');
        // International
        expect(marketTickers).toContain('VGK');
        expect(marketTickers).toContain('EWJ');
        // Gold
        expect(marketTickers).toContain('GLD');
        // WTI Crude Oil
        expect(marketTickers).toContain('USO');
        // VIX Volatility
        expect(marketTickers).toContain('VIXY');
    });

    it('deduplicates MACRO_TICKERS_LIST across categories', async () => {
        const { MACRO_TICKERS_LIST } = await import('./macro-tickers');
        const uniqueSet = new Set(MACRO_TICKERS_LIST);
        expect(MACRO_TICKERS_LIST.length).toBe(uniqueSet.size);
    });
});
