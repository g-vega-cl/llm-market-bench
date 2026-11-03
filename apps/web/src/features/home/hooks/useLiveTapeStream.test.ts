import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/fetch-intraday-tape', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../api/fetch-intraday-tape')>();
    return {
        ...actual,
        fetchLiveIntradayTape: vi.fn().mockResolvedValue({
            bars: [
                {
                    time: '2026-10-30T16:00:00Z',
                    open: 580.0,
                    high: 581.0,
                    low: 579.5,
                    close: 580.5,
                    volume: 1000,
                },
            ],
            agentState: null,
            isMarketOpen: true,
        }),
    };
});

import { fetchLiveIntradayTape } from '../api/fetch-intraday-tape';
import { useLiveTapeStream } from './useLiveTapeStream';

// Mock EventSource
class MockEventSource {
    static instances: MockEventSource[] = [];
    url: string;
    onopen: (() => void) | null = null;
    onerror: (() => void) | null = null;
    listeners: Record<string, ((e: MessageEvent) => void)[]> = {};
    closed = false;

    constructor(url: string) {
        this.url = url;
        MockEventSource.instances.push(this);
        setTimeout(() => {
            if (this.onopen && !this.closed) this.onopen();
        }, 0);
    }

    addEventListener(event: string, handler: (e: MessageEvent) => void) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(handler);
    }

    removeEventListener(event: string, handler: (e: MessageEvent) => void) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter((h) => h !== handler);
        }
    }

    emit(event: string, data: unknown) {
        const handlers = this.listeners[event] || [];
        const msg = new MessageEvent(event, { data: JSON.stringify(data) });
        for (const h of handlers) {
            h(msg);
        }
    }

    close() {
        this.closed = true;
    }
}

describe('useLiveTapeStream', () => {
    beforeEach(() => {
        MockEventSource.instances = [];
        vi.stubGlobal('EventSource', MockEventSource);
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('seeds with initialBars and connects to EventSource when market is open', async () => {
        const initialBars = [
            {
                time: '2026-10-30T16:00:00Z',
                open: 580.0,
                high: 581.0,
                low: 579.5,
                close: 580.5,
                volume: 1000,
            },
        ];

        const { result } = renderHook(() => useLiveTapeStream({ initialBars, isMarketOpen: true }));

        expect(result.current.bars).toEqual(initialBars);
        expect(MockEventSource.instances.length).toBe(1);
        expect(MockEventSource.instances[0].url).toContain('/api/tape/stream');
    });

    it('fetches tape via CSR on mount when initialBars is empty', async () => {
        const { result } = renderHook(() =>
            useLiveTapeStream({ initialBars: [], isMarketOpen: false }),
        );

        await act(async () => {
            await Promise.resolve();
        });

        expect(fetchLiveIntradayTape).toHaveBeenCalledTimes(1);
        expect(result.current.bars.length).toBe(1);
    });

    it('updates bars on snapshot and bar SSE events', async () => {
        const initialBars = [
            {
                time: '2026-10-30T16:00:00Z',
                open: 580.0,
                high: 581.0,
                low: 579.5,
                close: 580.5,
                volume: 1000,
            },
        ];

        const { result } = renderHook(() => useLiveTapeStream({ initialBars, isMarketOpen: true }));

        const es = MockEventSource.instances[0];

        // 1. Emit snapshot
        const snapshotBars = [
            ...initialBars,
            {
                time: '2026-10-30T16:01:00Z',
                open: 580.5,
                high: 581.5,
                low: 580.2,
                close: 581.2,
                volume: 1500,
            },
        ];

        act(() => {
            es.emit('snapshot', { bars: snapshotBars });
        });

        expect(result.current.bars).toHaveLength(2);

        // 2. Emit delta bar
        const updatedBar = {
            time: '2026-10-30T16:01:00Z',
            open: 580.5,
            high: 582.0,
            low: 580.2,
            close: 581.8,
            volume: 2200,
        };

        act(() => {
            es.emit('bar', { bar: updatedBar });
        });

        expect(result.current.bars).toHaveLength(2);
        expect(result.current.bars[1].close).toBe(581.8);
        expect(result.current.bars[1].high).toBe(582.0);
    });

    it('updates agentState on agent_turn SSE event and updates technicals on bar SSE event', async () => {
        const initialAgentState = {
            action: 'HOLD' as const,
            conviction: 50,
            thought: 'Watching support',
            marketDirection: 'NEUTRAL' as const,
            technicals: { vwap: 580.0, rsi_14: 50.0, trend: 'NEUTRAL' },
        };

        const { result } = renderHook(() =>
            useLiveTapeStream({ initialBars: [], initialAgentState, isMarketOpen: true }),
        );

        const es = MockEventSource.instances[0];

        // 1. Emit bar with technicals
        await act(async () => {
            es.emit('bar', {
                bar: {
                    time: '2026-10-30T16:02:00Z',
                    open: 581.0,
                    high: 582.5,
                    low: 581.0,
                    close: 582.2,
                    volume: 2500,
                },
                technicals: {
                    vwap: 581.5,
                    rsi_14: 65.0,
                    trend: 'BULLISH',
                },
            });
        });

        expect(result.current.agentState?.technicals?.vwap).toBe(581.5);
        expect(result.current.agentState?.technicals?.trend).toBe('BULLISH');

        // 2. Emit agent_turn
        await act(async () => {
            es.emit('agent_turn', {
                agent_state: {
                    action: 'BUY',
                    conviction: 85,
                    thought: 'Strong surge above VWAP',
                    marketDirection: 'BULLISH',
                    lastUpdated: '16:02 ET',
                },
            });
        });

        expect(result.current.agentState?.action).toBe('BUY');
        expect(result.current.agentState?.conviction).toBe(85);
        expect(result.current.agentState?.thought).toBe('Strong surge above VWAP');
    });

    it('disconnects EventSource on visibilitychange hidden to save battery and reconnects on visible', async () => {
        renderHook(() => useLiveTapeStream({ initialBars: [], isMarketOpen: true }));

        expect(MockEventSource.instances.length).toBe(1);
        const firstEs = MockEventSource.instances[0];
        expect(firstEs.closed).toBe(false);

        await act(async () => {
            await Promise.resolve();
        });

        // Hide tab
        Object.defineProperty(document, 'hidden', { value: true, configurable: true });
        act(() => {
            document.dispatchEvent(new Event('visibilitychange'));
        });

        expect(firstEs.closed).toBe(true);

        // Show tab again
        Object.defineProperty(document, 'hidden', { value: false, configurable: true });
        act(() => {
            document.dispatchEvent(new Event('visibilitychange'));
        });

        expect(MockEventSource.instances.length).toBe(2);
        expect(MockEventSource.instances[1].closed).toBe(false);

        await act(async () => {
            await Promise.resolve();
        });
    });
});
