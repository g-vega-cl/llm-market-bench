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
        const aaplPct = (((10 * 150) / totalInvested) * 100).toFixed(2) + '%';
        const tslaPct = (((5 * 700) / totalInvested) * 100).toFixed(2) + '%';
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
});
