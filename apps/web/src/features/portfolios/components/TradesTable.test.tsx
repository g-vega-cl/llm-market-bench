import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { type Trade, TradesTable } from './TradesTable';

const mockTrades: Trade[] = [
    {
        id: 't1',
        portfolio_id: 'p1',
        ticker: 'AAPL',
        signal: 'BUY',
        quantity: 10,
        price: 150,
        total_cost: 1500,
        executed_at: '2026-01-01T12:00:00Z',
        alpaca_status: 'FILLED',
        alpaca_order_id: 'alpaca-order-1',
        alpaca_submitted_at: '2026-01-01T12:00:00Z',
        alpaca_filled_at: '2026-01-01T12:05:00Z',
        realized_pnl: null,
        realized_pnl_pct: null,
        reasoning: 'Bullish momentum breakout.',
        decision_id: 'd1',
    },
    {
        id: 't2',
        portfolio_id: 'p1',
        ticker: 'TSLA',
        signal: 'SELL',
        quantity: 5,
        price: 700,
        total_cost: 3500,
        executed_at: '2026-01-02T12:00:00Z',
        alpaca_status: 'CANCELED',
        alpaca_order_id: 'alpaca-order-2',
        alpaca_submitted_at: '2026-01-02T12:00:00Z',
        alpaca_filled_at: null,
        realized_pnl: 100,
        realized_pnl_pct: 2.86,
        reasoning: 'Taking profit at target.',
        decision_id: 'd2',
    },
];

describe('TradesTable', () => {
    it('renders all trades in the table', () => {
        render(<TradesTable trades={mockTrades} />);
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.getByText('TSLA')).toBeInTheDocument();
        expect(screen.getByText('BUY')).toBeInTheDocument();
        expect(screen.getByText('SELL')).toBeInTheDocument();
        expect(screen.getByText('FILLED')).toBeInTheDocument();
        expect(screen.getByText('CANCELED')).toBeInTheDocument();
    });

    it('expands reasoning when a row is clicked', () => {
        render(<TradesTable trades={mockTrades} />);
        expect(screen.queryByText('Bullish momentum breakout.')).not.toBeInTheDocument();
        const aaplRow = screen.getByText('AAPL').closest('tr');
        expect(aaplRow).toBeInTheDocument();
        if (aaplRow) {
            fireEvent.click(aaplRow);
            expect(screen.getByText('Bullish momentum breakout.')).toBeInTheDocument();
            expect(screen.getByText('Thinking Process')).toBeInTheDocument();
            fireEvent.click(aaplRow);
            expect(screen.queryByText('Bullish momentum breakout.')).not.toBeInTheDocument();
        }
    });

    it('applies the min-width to the inner table rather than the container', () => {
        const { container } = render(<TradesTable trades={mockTrades} />);
        const outerWrapper = container.firstChild as HTMLElement;
        expect(outerWrapper).toBeInTheDocument();
        expect(outerWrapper.className).not.toContain('min-w-[700px]');

        const table = container.querySelector('table');
        expect(table).toBeInTheDocument();
        expect(table?.className).toContain('min-w-[700px]');
    });
});
