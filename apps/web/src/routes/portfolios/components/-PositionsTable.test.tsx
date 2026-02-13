import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PositionsTable, Position } from './-PositionsTable'

const mockPositions: Position[] = [
    {
        ticker: 'AAPL',
        quantity: 10,
        average_cost_basis: 150,
        current_price: 160,
        unrealized_pnl_usd: 100,
        unrealized_pnl_pct: 6.67,
        reasoning: 'Strong iPhone sales and services growth.'
    },
    {
        ticker: 'TSLA',
        quantity: 5,
        average_cost_basis: 700,
        current_price: 650,
        unrealized_pnl_usd: -250,
        unrealized_pnl_pct: -7.14,
        reasoning: 'Macro headwinds affecting EV demand.'
    }
]

describe('PositionsTable', () => {
    it('renders all positions in the table', () => {
        render(<PositionsTable positions={mockPositions} />)
        expect(screen.getByText('AAPL')).toBeInTheDocument()
        expect(screen.getByText('TSLA')).toBeInTheDocument()
        expect(screen.getByText('10')).toBeInTheDocument()
        expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('expands reasoning when a row is clicked', () => {
        render(<PositionsTable positions={mockPositions} />)

        // Reasoning should not be visible initially
        expect(screen.queryByText('Strong iPhone sales and services growth.')).not.toBeInTheDocument()

        // Click the AAPL row
        const aaplRow = screen.getByTestId('position-row-AAPL')
        fireEvent.click(aaplRow)

        // Reasoning should now be visible
        expect(screen.getByText('Strong iPhone sales and services growth.')).toBeInTheDocument()
        expect(screen.getByText('Thinking Process')).toBeInTheDocument()

        // Click again to collapse
        fireEvent.click(aaplRow)
        expect(screen.queryByText('Strong iPhone sales and services growth.')).not.toBeInTheDocument()
    })

    it('shows empty state when no positions are provided', () => {
        render(<PositionsTable positions={[]} />)
        expect(screen.getByText('No active positions in this portfolio.')).toBeInTheDocument()
    })

    it('formats currency and percentages correctly', () => {
        render(<PositionsTable positions={mockPositions} />)
        expect(screen.getByText('$150.00')).toBeInTheDocument()
        expect(screen.getByText('$160.00')).toBeInTheDocument()
        expect(screen.queryByText('+100.00%')).not.toBeInTheDocument()
        expect(screen.getByText((_, el) => el?.textContent === '+$100.00')).toBeInTheDocument()
        expect(screen.getByText((_, el) => el?.textContent === '+6.67%')).toBeInTheDocument()
        expect(screen.getByText((_, el) => el?.textContent === '$-250.00')).toBeInTheDocument()
        expect(screen.getByText((_, el) => el?.textContent === '-7.14%')).toBeInTheDocument()
    })
})
