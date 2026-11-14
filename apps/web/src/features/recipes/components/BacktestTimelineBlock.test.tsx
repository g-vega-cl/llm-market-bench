import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { BacktestResultData } from '../types';
import { BacktestTimelineBlock } from './BacktestTimelineBlock';

const partialResults: BacktestResultData = {
    window_dates: ['2026-08-03', '2026-08-04', '2026-08-05'],
    days_completed: 1,
    total_days: 3,
    current_day: '2026-08-04',
    total_return_pct_midpoint: 0,
    total_return_pct_net: 0,
    total_trades: 0,
    win_rate_pct: 0,
    max_drawdown_pct: 0,
    equity_curve: [{ time: '2026-08-03', equity: 10000 }],
    trades: [],
    day_steps: [
        {
            day: '2026-08-03',
            day_index: 0,
            status: 'completed',
            signals: [{ action: 'SELL', ticker: 'AMD' }],
            tool_calls: ['get_stock_quote({"ticker":"AMD"})'],
            output_excerpt: '[{"action": "SELL", "ticker": "AMD"}]',
            day_pnl_net: -12.5,
            trades_executed: 1,
            trades_skipped: 0,
        },
    ],
};

describe('BacktestTimelineBlock', () => {
    it('renders queue waiting trough before window dates exist', () => {
        render(<BacktestTimelineBlock status="pending" results={null} />);
        expect(
            screen.getByText(/Waiting for recipe worker to pick a 2-week historical window/i),
        ).toBeInTheDocument();
    });

    it('renders settled, running, and queued day tiles and inspects clicked day in-flow', () => {
        render(<BacktestTimelineBlock status="processing" results={partialResults} />);

        expect(screen.getByText('1 / 3 Days Settled')).toBeInTheDocument();
        expect(screen.getByText('SELL AMD')).toBeInTheDocument();
        expect(screen.getByText('-$12.50')).toBeInTheDocument();
        expect(screen.getByText('RUNNING')).toBeInTheDocument();
        expect(screen.getByText('QUEUED')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /2026-08-04/ }));
        expect(screen.getByText('Running LLM evaluation for this session...')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /2026-08-03/ }));
        expect(screen.getByText('get_stock_quote({"ticker":"AMD"})')).toBeInTheDocument();
        expect(screen.getByText('[{"action": "SELL", "ticker": "AMD"}]')).toBeInTheDocument();
    });
});
