import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { BacktestResultData } from '../types';
import { RecipeBacktestResults } from './RecipeBacktestResults';

const base: BacktestResultData = {
    ending_capital_midpoint: 9800,
    ending_capital_net: 9750,
    total_return_pct_midpoint: -2.0,
    total_return_pct_net: -2.5,
    total_trades: 2,
    winning_trades: 1,
    win_rate_pct: 50,
    profit_factor: 0.8,
    max_drawdown_pct: 3.2,
    llm_calls_made: 6,
    equity_curve: [],
    trades: [],
};

describe('RecipeBacktestResults states', () => {
    it('renders the loading state', () => {
        render(<RecipeBacktestResults results={null} isLoading />);
        expect(screen.getByText('Executing Timeline Simulation...')).toBeInTheDocument();
    });

    it('renders the empty state when there are no results', () => {
        render(<RecipeBacktestResults results={null} />);
        expect(screen.getByText('No Backtest Results Yet')).toBeInTheDocument();
    });

    it('prefers loading over results while a run is in flight', () => {
        render(<RecipeBacktestResults results={base} isLoading />);
        expect(screen.getByText('Executing Timeline Simulation...')).toBeInTheDocument();
        expect(screen.queryByText('Simulation Telemetry')).not.toBeInTheDocument();
    });
});

describe('RecipeBacktestResults telemetry', () => {
    it('shows negative return without a plus sign and formats stats', () => {
        render(<RecipeBacktestResults results={base} />);
        expect(screen.getByText('-2.50%')).toBeInTheDocument();
        expect(screen.getByText('$9,750.00')).toBeInTheDocument();
        expect(screen.getByText('50% (1/2)')).toBeInTheDocument();
        expect(screen.getByText('-3.2%')).toBeInTheDocument();
        expect(screen.getByText('6')).toBeInTheDocument();
    });

    it('falls back to 10,000 starting capital when ending capital is missing', () => {
        render(
            <RecipeBacktestResults
                results={{
                    ...base,
                    ending_capital_net: undefined,
                    ending_capital_midpoint: undefined,
                }}
            />,
        );
        expect(screen.getByText('$10,000.00')).toBeInTheDocument();
    });

    it('omits optional tables when there is nothing to show', () => {
        render(<RecipeBacktestResults results={base} />);
        expect(screen.queryByText(/Counterfactual Skipped Signals/)).not.toBeInTheDocument();
        expect(screen.queryByText(/Executed Trades/)).not.toBeInTheDocument();
    });
});

describe('RecipeBacktestResults tables', () => {
    it('renders executed trades with signed returns', () => {
        render(
            <RecipeBacktestResults
                results={{
                    ...base,
                    trades: [
                        {
                            ticker: 'NVDA',
                            entry_time: '2026-03-02T15:00:00Z',
                            entry_price: 100,
                            exit_time: '2026-03-02T16:00:00Z',
                            exit_price: 103.5,
                            action: 'BUY',
                            pnl_midpoint: 36,
                            pnl_net: 35,
                            return_pct_midpoint: 3.6,
                            return_pct_net: 3.5,
                            exit_reason: 'take_profit',
                            confidence: 0.8,
                        },
                        {
                            ticker: 'AMD',
                            entry_time: '2026-03-03T15:00:00Z',
                            entry_price: 50,
                            exit_time: '2026-03-03T16:00:00Z',
                            exit_price: 49,
                            action: 'SELL',
                            pnl_midpoint: -10,
                            pnl_net: -11,
                            return_pct_midpoint: -2.0,
                            return_pct_net: -2.2,
                            exit_reason: 'stop_loss',
                            confidence: 0.6,
                        },
                    ],
                }}
            />,
        );
        expect(screen.getByText('Executed Trades (2)')).toBeInTheDocument();
        expect(screen.getByText('BUY NVDA')).toBeInTheDocument();
        expect(screen.getByText('SELL AMD')).toBeInTheDocument();
        expect(screen.getByText('+3.50%')).toBeInTheDocument();
        expect(screen.getByText('-2.20%')).toBeInTheDocument();
        expect(screen.getByText('$103.50')).toBeInTheDocument();
        expect(screen.getByText('$-11.00')).toBeInTheDocument();
        expect(screen.getByText('take_profit')).toBeInTheDocument();
    });

    it('caps skipped signals at 15 rows and hides empty headlines', () => {
        const skipped = Array.from({ length: 20 }, (_, i) => ({
            time: `2026-03-02T15:${String(i).padStart(2, '0')}:00Z`,
            reason: `reason-${i}`,
            skip_type: 'LLM_REJECTED',
        }));
        render(<RecipeBacktestResults results={{ ...base, skipped_trades: skipped }} />);
        expect(screen.getByText('Counterfactual Skipped Signals (20)')).toBeInTheDocument();
        expect(screen.getByText('reason-14')).toBeInTheDocument();
        expect(screen.queryByText('reason-15')).not.toBeInTheDocument();
        expect(screen.queryByText(/Catalyst:/)).not.toBeInTheDocument();
    });
});
