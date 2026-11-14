import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { BacktestResultData } from '../types';
import { BacktestTelemetryBlock } from './BacktestTelemetryBlock';

const results: BacktestResultData = {
    window_dates: ['2026-08-03', '2026-08-04'],
    starting_capital: 10000,
    ending_capital_midpoint: 10200,
    ending_capital_net: 10180,
    total_return_pct_midpoint: 2.0,
    total_return_pct_net: 1.8,
    total_trades: 2,
    winning_trades: 2,
    losing_trades: 0,
    win_rate_pct: 100,
    profit_factor: 99,
    max_drawdown_pct: 0.4,
    llm_calls_made: 2,
    equity_curve: [
        { time: '2026-08-03', equity: 10090 },
        { time: '2026-08-04', equity: 10180 },
    ],
    trades: [],
};

describe('BacktestTelemetryBlock', () => {
    it('renders live metric tiles, equity progression, and switches P&L mode', () => {
        render(<BacktestTelemetryBlock results={results} isRunning />);

        expect(screen.getAllByText('$10,180.00').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('+1.80%')).toBeInTheDocument();
        expect(screen.getByText('2 / 2')).toBeInTheDocument();
        expect(screen.getByText('2026-08-03')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Midpoint (Zero-Cost)' }));
        expect(screen.getByText('$10,200.00')).toBeInTheDocument();
        expect(screen.getByText('+2.00%')).toBeInTheDocument();
    });
});
