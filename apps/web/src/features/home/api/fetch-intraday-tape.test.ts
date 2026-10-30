import { describe, expect, it } from 'vitest';
import type { CandlestickBar } from '../components/SPYCandlestickChart';
import {
    buildAgentState,
    filterLastBars,
    isRegularMarketHours,
    mergeIncomingBar,
} from './fetch-intraday-tape';

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

    describe('mergeIncomingBar', () => {
        const baseBar: CandlestickBar = {
            time: '2026-10-30T16:00:00Z',
            open: 580.0,
            high: 581.0,
            low: 579.5,
            close: 580.5,
            volume: 1000,
        };

        it('initializes array with incoming bar when current tape is empty', () => {
            expect(mergeIncomingBar([], baseBar)).toEqual([baseBar]);
            expect(mergeIncomingBar(null, baseBar)).toEqual([baseBar]);
            expect(mergeIncomingBar([baseBar], null)).toEqual([baseBar]);
        });

        it('mutates forming bar in place when timestamp matches last bar', () => {
            const updatedTick: CandlestickBar = {
                time: '2026-10-30T16:00:00Z',
                open: 580.0,
                high: 582.0, // higher
                low: 579.0, // lower
                close: 581.5, // new close
                volume: 2500, // expanded volume
            };

            const result = mergeIncomingBar([baseBar], updatedTick);
            expect(result).toHaveLength(1);
            expect(result[0].open).toBe(580.0);
            expect(result[0].high).toBe(582.0);
            expect(result[0].low).toBe(579.0);
            expect(result[0].close).toBe(581.5);
            expect(result[0].volume).toBe(2500);
        });

        it('appends and shifts window when a new minute rolls over', () => {
            const nextMinuteBar: CandlestickBar = {
                time: '2026-10-30T16:01:00Z',
                open: 581.5,
                high: 582.5,
                low: 581.0,
                close: 582.2,
                volume: 1200,
            };

            const result = mergeIncomingBar([baseBar], nextMinuteBar, 2);
            expect(result).toHaveLength(2);
            expect(result[0]).toEqual(baseBar);
            expect(result[1]).toEqual(nextMinuteBar);

            // Roll over 3rd bar with maxBars = 2 -> shifts oldest out
            const thirdBar: CandlestickBar = {
                time: '2026-10-30T16:02:00Z',
                open: 582.2,
                high: 583.0,
                low: 582.0,
                close: 582.8,
                volume: 1100,
            };
            const rolled = mergeIncomingBar(result, thirdBar, 2);
            expect(rolled).toHaveLength(2);
            expect(rolled[0]).toEqual(nextMinuteBar);
            expect(rolled[1]).toEqual(thirdBar);
        });

        it('ignores out-of-order or stale bar timestamps', () => {
            const staleBar: CandlestickBar = {
                time: '2026-10-30T15:59:00Z',
                open: 578.0,
                high: 579.0,
                low: 577.5,
                close: 578.5,
                volume: 800,
            };
            const result = mergeIncomingBar([baseBar], staleBar);
            expect(result).toEqual([baseBar]);
        });
    });
});
