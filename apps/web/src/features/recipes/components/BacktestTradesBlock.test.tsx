import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { BacktestResultData } from '../types';
import { BacktestTradesBlock } from './BacktestTradesBlock';

const results: BacktestResultData = {
    total_return_pct_midpoint: 1.5,
    total_return_pct_net: 1.4,
    total_trades: 1,
    win_rate_pct: 100,
    max_drawdown_pct: 0,
    equity_curve: [],
    trades: [
        {
            ticker: 'NVDA',
            action: 'BUY',
            entry_time: '2026-08-03',
            entry_price: 110.25,
            exit_time: '2026-08-05 15:30 ET',
            exit_price: 115.5,
            pnl_midpoint: 47.62,
            pnl_net: 46.62,
            return_pct_midpoint: 4.76,
            return_pct_net: 4.66,
            exit_reason: 'END_OF_WINDOW',
            confidence: 100,
        },
    ],
    skipped_trades: [
        {
            time: '2026-08-14',
            skip_type: 'NO_PRICE_DATA',
            reason: 'Missing daily bar for NVDA on 2026-08-14 -> EOF',
        },
    ],
};

describe('BacktestTradesBlock', () => {
    it('renders empty notice before trades settle', () => {
        render(<BacktestTradesBlock results={null} />);
        expect(screen.getByText(/No trades executed yet/i)).toBeInTheDocument();
    });

    it('renders executed trades with exit reason, right-aligned numeric columns, and skipped signals', () => {
        render(<BacktestTradesBlock results={results} />);

        expect(screen.getByText('Executed Trades (1)')).toBeInTheDocument();
        expect(screen.getByText('BUY NVDA')).toBeInTheDocument();
        expect(screen.getByText('END_OF_WINDOW')).toBeInTheDocument();
        expect(screen.getByText('+$46.62')).toBeInTheDocument();
        expect(screen.getByText('Counterfactual Skipped Signals (1)')).toBeInTheDocument();
        expect(screen.getByText('NO_PRICE_DATA')).toBeInTheDocument();

        const entryHeader = screen.getByRole('columnheader', { name: 'Entry' });
        expect(entryHeader).toHaveClass('text-right');
    });

    it('renders open BUY positions with an OPEN badge alongside closed trades so BUY NVDA is never hidden', () => {
        const withOpen: BacktestResultData = {
            ...results,
            open_positions: [
                {
                    ticker: 'AMD',
                    shares: 10,
                    entry_price: 150,
                    entry_time: '2026-08-04 09:30 ET',
                    cost_basis: 1500,
                    current_price: 156,
                    market_value: 1559.22,
                    unrealized_pnl_net: 59.22,
                    unrealized_return_pct: 3.95,
                },
            ],
        };
        render(<BacktestTradesBlock results={withOpen} />);

        expect(screen.getByText('Executed Trades (2)')).toBeInTheDocument();
        expect(screen.getByText('BUY AMD')).toBeInTheDocument();
        expect(screen.getByText('OPEN')).toBeInTheDocument();
        expect(screen.getByText('+$59.22')).toBeInTheDocument();
    });
});
