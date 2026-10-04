import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { type Position, PositionsTable } from './PositionsTable';

const mockPositions: Position[] = [
    {
        position_id: '1',
        portfolio_id: 'p1',
        owner_id: 'owner1',
        ticker: 'AAPL',
        quantity: 10,
        average_cost_basis: 150,
        current_price: 160,
        price_fetched_at: '2026-01-01',
        unrealized_pnl_usd: 100,
        unrealized_pnl_pct: 6.67,
        reasoning: 'Strong iPhone sales and services growth.',
    },
    {
        position_id: '2',
        portfolio_id: 'p1',
        owner_id: 'owner1',
        ticker: 'TSLA',
        quantity: 5,
        average_cost_basis: 700,
        current_price: 650,
        price_fetched_at: '2026-01-01',
        unrealized_pnl_usd: -250,
        unrealized_pnl_pct: -7.14,
        reasoning: 'Macro headwinds affecting EV demand.',
    },
];

// Calculate expected invested cash and percentages
const totalInvested = mockPositions.reduce(
    (sum, p) => sum + (p.quantity ?? 0) * (p.average_cost_basis ?? 0),
    0,
);

describe('PositionsTable', () => {
    it('renders all positions in the table', () => {
        render(<PositionsTable positions={mockPositions} />);
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.getByText('TSLA')).toBeInTheDocument();
        expect(screen.getByText('10')).toBeInTheDocument();
        expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('expands reasoning when a row is clicked', () => {
        render(<PositionsTable positions={mockPositions} />);
        expect(
            screen.queryByText('Strong iPhone sales and services growth.'),
        ).not.toBeInTheDocument();
        const aaplRow = screen.getByTestId('position-row-AAPL');
        fireEvent.click(aaplRow);
        expect(screen.getByText('Strong iPhone sales and services growth.')).toBeInTheDocument();
        expect(screen.getByText('Thinking Process')).toBeInTheDocument();
        fireEvent.click(aaplRow);
        expect(
            screen.queryByText('Strong iPhone sales and services growth.'),
        ).not.toBeInTheDocument();
    });

    it('shows empty state when no positions are provided', () => {
        render(<PositionsTable positions={[]} />);
        expect(screen.getByText('No active positions in this portfolio.')).toBeInTheDocument();
    });

    it('displays invested cash and portfolio percentage correctly', () => {
        render(<PositionsTable positions={mockPositions} />);
        // Invested cash values
        expect(
            screen.getByText(
                `$${(10 * 150).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            ),
        ).toBeInTheDocument();
        expect(
            screen.getByText(
                `$${(5 * 700).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            ),
        ).toBeInTheDocument();
        // Percentage values
        const aaplPct = `${(((10 * 150) / totalInvested) * 100).toFixed(2)}%`;
        const tslaPct = `${(((5 * 700) / totalInvested) * 100).toFixed(2)}%`;
        expect(screen.getByText(aaplPct)).toBeInTheDocument();
        expect(screen.getByText(tslaPct)).toBeInTheDocument();
    });

    it('formats currency and percentages correctly', () => {
        render(<PositionsTable positions={mockPositions} />);
        expect(screen.getByText('$150.00')).toBeInTheDocument();
        expect(screen.getByText('$160.00')).toBeInTheDocument();
        expect(screen.getByText((_, el) => el?.textContent === '+$100.00')).toBeInTheDocument();
        expect(screen.getByText((_, el) => el?.textContent === '+6.67%')).toBeInTheDocument();
        expect(screen.getByText((_, el) => el?.textContent === '$-250.00')).toBeInTheDocument();
        expect(screen.getByText((_, el) => el?.textContent === '-7.14%')).toBeInTheDocument();
    });

    it('applies the min-width to the inner table rather than the container', () => {
        const { container } = render(<PositionsTable positions={mockPositions} />);
        const outerWrapper = container.firstChild as HTMLElement;
        expect(outerWrapper).toBeInTheDocument();
        expect(outerWrapper.className).not.toContain('min-w-[800px]');

        const table = container.querySelector('table');
        expect(table).toBeInTheDocument();
        expect(table?.className).toContain('min-w-[800px]');
    });

    it('displays exact bought time in expanded row when trades are provided', () => {
        const mockBuyTrades = [
            {
                id: 't-aapl',
                portfolio_id: 'p1',
                ticker: 'AAPL',
                signal: 'BUY',
                quantity: 10,
                price: 150,
                total_cost: 1500,
                executed_at: '2026-01-01T12:00:00Z',
                alpaca_status: 'FILLED',
                alpaca_order_id: null,
                alpaca_submitted_at: null,
                alpaca_filled_at: null,
                realized_pnl: null,
                realized_pnl_pct: null,
                decision_id: null,
                reasoning: 'Momentum entry.',
            },
        ];

        render(<PositionsTable positions={mockPositions} trades={mockBuyTrades} />);
        const aaplRow = screen.getByTestId('position-row-AAPL');
        fireEvent.click(aaplRow);

        expect(screen.getByText(/Bought:/i)).toBeInTheDocument();
        expect(screen.getByText(/7:00:00 AM ET/)).toBeInTheDocument();
    });

    it('renders short positions with SHORT badge and Sold Short timestamp', () => {
        const mockPositionsWithShort: Position[] = [
            {
                position_id: '3',
                portfolio_id: 'p1',
                owner_id: 'owner1',
                ticker: 'XHB',
                quantity: 26,
                average_cost_basis: 96.55,
                current_price: 94.2,
                price_fetched_at: '2026-10-02',
                unrealized_pnl_usd: 61.1,
                unrealized_pnl_pct: 2.43,
                reasoning: 'Weak housing starts and rate sensitivity.',
                side: 'SHORT',
            },
        ];

        const mockShortTrades = [
            {
                id: 't-xhb',
                portfolio_id: 'p1',
                ticker: 'XHB',
                signal: 'SHORT',
                quantity: 26,
                price: 96.55,
                total_cost: 2510.3,
                executed_at: '2026-10-02T13:35:00Z',
                alpaca_status: null,
                alpaca_order_id: null,
                alpaca_submitted_at: null,
                alpaca_filled_at: null,
                realized_pnl: null,
                realized_pnl_pct: null,
                decision_id: null,
                reasoning: 'Systematic short entry.',
            },
        ];

        render(<PositionsTable positions={mockPositionsWithShort} trades={mockShortTrades} />);
        expect(screen.getByText('XHB')).toBeInTheDocument();
        expect(screen.getByText('SHORT')).toBeInTheDocument();

        const xhbRow = screen.getByTestId('position-row-XHB');
        fireEvent.click(xhbRow);

        expect(screen.getByText(/Sold Short:/i)).toBeInTheDocument();
        expect(screen.getByText(/9:35:00 AM ET/)).toBeInTheDocument();
    });
});
