import { describe, expect, it } from 'vitest';
import type { CandlestickBar } from '../components/SPYCandlestickChart';
import { buildAgentState, filterLastBars, isRegularMarketHours } from './fetch-intraday-tape';

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

    it('builds live agent state from feeling and trades payload', () => {
        const feeling = {
            confidence_score: 88,
            why_explanation: 'Holding support above 20 EMA',
            market_direction: 'BULLISH',
            sentiment_label: 'Momentum Breakout',
            model_used: 'Strata Orca',
            created_at: '2026-10-29T19:30:00Z',
        };
        const payload = {
            action: 'BUY' as const,
            technicals: { vwap: 582.5, rsi_14: 61.2, trend: 'BULLISH' },
            memories_consulted: ['Memory 1'],
        };

        const state = buildAgentState(feeling, payload);
        expect(state.action).toBe('BUY');
        expect(state.conviction).toBe(88);
        expect(state.marketDirection).toBe('BULLISH');
        expect(state.sentimentLabel).toBe('Momentum Breakout');
        expect(state.technicals?.vwap).toBe(582.5);
    });
});
