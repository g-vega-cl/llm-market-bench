import { describe, expect, it } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import type { LivePortfolioSnapshot, RecipeJobRecord } from '../types';
import { computeBotBehaviors, deriveOverviewMetrics } from './recipe-insights';

const basePortfolio: LivePortfolioSnapshot = {
    cash: 7500,
    total_equity: 10300,
    open_positions: [
        {
            ticker: 'NVDA',
            shares: 10,
            entry_price: 250,
            entry_time: '2026-11-14 09:30 ET',
            current_price: 280,
            market_value: 2800,
            cost_basis: 2500,
            unrealized_pnl_net: 300,
            unrealized_return_pct: 12,
        },
    ],
    trades: [
        {
            ticker: 'AMD',
            action: 'BUY',
            entry_time: '2026-11-12 09:30 ET',
            entry_price: 150,
            exit_time: '2026-11-13 15:30 ET',
            exit_price: 165,
            pnl_midpoint: 150,
            pnl_net: 145,
            return_pct_midpoint: 10,
            return_pct_net: 9.6,
            exit_reason: 'TARGET_HIT',
            confidence: 88,
        },
        {
            ticker: 'INTC',
            action: 'BUY',
            entry_time: '2026-11-12 10:00 ET',
            entry_price: 25,
            exit_time: '2026-11-13 14:00 ET',
            exit_price: 24,
            pnl_midpoint: -40,
            pnl_net: -45,
            return_pct_midpoint: -4,
            return_pct_net: -4.5,
            exit_reason: 'STOP_LOSS',
            confidence: 72,
        },
    ],
    equity_curve: [
        { time: '2026-11-12 09:30 ET', equity: 10000 },
        { time: '2026-11-14 15:30 ET', equity: 10300 },
    ],
};

const sampleLiveRuns: RecipeJobRecord[] = [
    {
        id: 'live-2',
        mode: 'live_turn',
        status: 'completed',
        progress_pct: 100,
        error_message: null,
        created_at: '2026-11-14T15:30:00Z',
        result_json: {
            mode: 'live_turn',
            as_of_utc: '2026-11-14T15:30:00Z',
            stages: [
                {
                    stage_id: 's1',
                    prompt: 'Check NVDA',
                    output: 'Holding NVDA position while momentum stays strong.',
                    tool_calls: ['get_technical_indicators', 'get_ticker_news'],
                },
            ],
            final_output: 'Holding NVDA position while momentum stays strong.',
            signals: [],
        },
    },
    {
        id: 'live-1',
        mode: 'live_turn',
        status: 'completed',
        progress_pct: 100,
        error_message: null,
        created_at: '2026-11-14T09:30:00Z',
        result_json: {
            mode: 'live_turn',
            as_of_utc: '2026-11-14T09:30:00Z',
            stages: [
                {
                    stage_id: 's1',
                    prompt: 'Buy NVDA',
                    output: 'Buying NVDA on AI capex catalyst.',
                    tool_calls: ['get_ticker_news'],
                },
            ],
            final_output: 'Buying NVDA on AI capex catalyst.',
            signals: [{ action: 'BUY', ticker: 'NVDA' }],
        },
    },
];

const sampleBacktests: RecipeJobRecord[] = [
    {
        id: 'bt-1',
        mode: 'backtest',
        status: 'completed',
        progress_pct: 100,
        error_message: null,
        created_at: '2026-11-10T10:00:00Z',
        result_json: {
            mode: 'backtest',
            starting_capital: 10000,
            ending_capital_net: 10850,
            cash: 10850,
            total_equity: 10850,
            total_return_pct_midpoint: 9.0,
            total_return_pct_net: 8.5,
            total_trades: 4,
            winning_trades: 3,
            win_rate_pct: 75,
            max_drawdown_pct: 2.1,
            equity_curve: [
                { time: '2026-11-01', equity: 10000 },
                { time: '2026-11-08', equity: 10850 },
            ],
            trades: [
                {
                    ticker: 'MSFT',
                    action: 'BUY',
                    entry_time: '2026-11-02',
                    entry_price: 400,
                    exit_time: '2026-11-04',
                    exit_price: 420,
                    pnl_midpoint: 200,
                    pnl_net: 195,
                    return_pct_midpoint: 5,
                    return_pct_net: 4.8,
                    exit_reason: 'TARGET_HIT',
                    confidence: 90,
                },
            ],
            skipped_trades: [{ time: '2026-11-03', reason: 'Max slots', skip_type: 'MAX_OPEN' }],
            day_steps: [
                {
                    day: '2026-11-02',
                    day_index: 0,
                    status: 'completed',
                    signals: [{ action: 'BUY', ticker: 'MSFT' }],
                    tool_calls: ['get_key_metrics'],
                    output_excerpt: 'Buy MSFT on cloud beat.',
                    day_pnl_net: 195,
                    trades_executed: 1,
                    trades_skipped: 0,
                },
            ],
        },
    },
];

describe('computeBotBehaviors & deriveOverviewMetrics', () => {
    it('computes live behavioral insights, tool footprint, ticker wins, and exit reasons', () => {
        const behaviors = computeBotBehaviors({
            strategy: STARTER_RECIPES[0],
            liveRuns: sampleLiveRuns,
            trades: basePortfolio.trades,
            backtests: sampleBacktests,
        });

        expect(behaviors.source).toBe('live');
        expect(behaviors.actionMix).toEqual({
            buyCount: 1,
            exitCount: 0,
            sellCount: 0,
            holdCount: 1,
            totalTurns: 2,
            skippedCount: 0,
        });
        expect(behaviors.topTickers.map((t) => t.ticker)).toContain('AMD');
        expect(behaviors.exitReasons).toEqual([
            { reason: 'STOP_LOSS', count: 1, wins: 0 },
            { reason: 'TARGET_HIT', count: 1, wins: 1 },
        ]);
        expect(behaviors.toolUsage[0]).toMatchObject({
            name: 'get_ticker_news',
            label: 'Ticker News',
            count: 2,
            pct: 100,
        });
        expect(behaviors.latestDecision).toMatchObject({
            jobId: 'live-2',
            mode: 'live_turn',
            excerpt: 'Holding NVDA position while momentum stays strong.',
        });

        const metrics = deriveOverviewMetrics({
            portfolio: basePortfolio,
            liveRuns: sampleLiveRuns,
            backtests: sampleBacktests,
        });
        expect(metrics).toMatchObject({
            mode: 'live',
            totalEquity: 10300,
            cash: 7500,
            netReturnPct: 3,
            winRatePct: 50,
            closedTradesCount: 2,
            winningTradesCount: 1,
            openPositionsCount: 1,
        });
    });

    it('falls back gracefully to the latest completed backtest when no live turns exist', () => {
        const emptyLivePortfolio: LivePortfolioSnapshot = {
            cash: 10000,
            total_equity: 10000,
            open_positions: [],
            trades: [],
            equity_curve: [],
        };

        const behaviors = computeBotBehaviors({
            strategy: STARTER_RECIPES[0],
            liveRuns: [],
            trades: [],
            backtests: sampleBacktests,
        });
        expect(behaviors.source).toBe('backtest');
        expect(behaviors.actionMix.buyCount).toBe(1);
        expect(behaviors.actionMix.skippedCount).toBe(1);
        expect(behaviors.latestDecision?.mode).toBe('backtest');
        expect(behaviors.latestDecision?.jobId).toBe('bt-1');

        const metrics = deriveOverviewMetrics({
            portfolio: emptyLivePortfolio,
            liveRuns: [],
            backtests: sampleBacktests,
        });
        expect(metrics).toMatchObject({
            mode: 'backtest',
            totalEquity: 10850,
            netReturnPct: 8.5,
            winRatePct: 75,
            latestBacktestJobId: 'bt-1',
        });
    });

    it('returns clean empty/none metrics and configured tools when no runs exist', () => {
        const emptyLivePortfolio: LivePortfolioSnapshot = {
            cash: 10000,
            total_equity: 10000,
            open_positions: [],
            trades: [],
            equity_curve: [],
        };

        const behaviors = computeBotBehaviors({
            strategy: STARTER_RECIPES[0],
            liveRuns: [],
            trades: [],
            backtests: [],
        });
        expect(behaviors.source).toBe('none');
        expect(behaviors.latestDecision).toBeNull();
        expect(behaviors.toolUsage.length).toBeGreaterThan(0);

        const metrics = deriveOverviewMetrics({
            portfolio: emptyLivePortfolio,
            liveRuns: [],
            backtests: [],
        });
        expect(metrics.mode).toBe('none');
        expect(metrics.netReturnPct).toBeNull();
        expect(metrics.winRatePct).toBeNull();
    });
});
