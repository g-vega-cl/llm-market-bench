import { STARTER_RECIPES } from '../starter-templates';
import type { RecipeOverviewData } from '../types';

/** Shared Overview fixture for the hub and detail page suites. */
export const liveOverviewData: RecipeOverviewData = {
    recipeId: 'rec-live-1',
    strategy: { ...STARTER_RECIPES[0], id: 'rec-live-1', name: 'AI Capex Radar' },
    isOwner: true,
    isPublic: false,
    isTemplate: false,
    isLive: true,
    turboExpiresAt: null,
    turboUsedToday: false,
    portfolio: {
        cash: 7500,
        total_equity: 10500,
        open_positions: [
            {
                ticker: 'NVDA',
                shares: 10,
                entry_price: 250,
                entry_time: '2026-11-14 09:30 ET',
                current_price: 300,
                market_value: 3000,
                cost_basis: 2500,
                unrealized_pnl_net: 500,
                unrealized_return_pct: 20,
            },
        ],
        trades: [
            {
                ticker: 'AVGO',
                action: 'BUY',
                entry_time: '2026-11-12 09:30 ET',
                entry_price: 180,
                exit_time: '2026-11-13 15:30 ET',
                exit_price: 190,
                pnl_midpoint: 100,
                pnl_net: 96,
                return_pct_midpoint: 5.5,
                return_pct_net: 5.2,
                exit_reason: 'TARGET_HIT',
                catalyst_headline: 'Custom ASIC demand surge',
                confidence: 86,
            },
        ],
        equity_curve: [
            { time: '2026-11-14 09:30 ET', equity: 10000 },
            { time: '2026-11-18 15:30 ET', equity: 10500 },
        ],
    },
    recentLiveRuns: [
        {
            id: 'live-run-1',
            recipe_id: 'rec-live-1',
            mode: 'live_turn',
            status: 'completed',
            progress_pct: 100,
            result_json: {
                mode: 'live_turn',
                as_of_utc: '2026-11-18T15:30:00Z',
                stages: [
                    {
                        stage_id: 's1',
                        prompt: 'Evaluate NVDA',
                        output: 'Maintaining NVDA long on data center strength.',
                        tool_calls: ['get_ticker_news'],
                    },
                ],
                final_output: 'Maintaining NVDA long on data center strength.',
                signals: [{ action: 'BUY', ticker: 'NVDA' }],
            },
            error_message: null,
            created_at: '2026-11-18T15:30:00Z',
        },
    ],
    recentBacktests: [
        {
            id: 'bt-job-1',
            recipe_id: 'rec-live-1',
            mode: 'backtest',
            status: 'completed',
            progress_pct: 100,
            result_json: {
                mode: 'backtest',
                window_dates: ['2026-11-01', '2026-11-14'],
                total_return_pct_midpoint: 7.2,
                total_return_pct_net: 6.8,
                total_trades: 3,
                win_rate_pct: 66.7,
                max_drawdown_pct: 1.8,
                equity_curve: [],
                trades: [],
            },
            error_message: null,
            created_at: '2026-11-10T10:00:00Z',
        },
    ],
};
