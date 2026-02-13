import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { TradesTable, Trade } from './-TradesTable'

const mockTrades: Trade[] = [
    {
        id: 't1',
        ticker: 'AAPL',
        signal: 'BUY',
        quantity: 10,
        price: 150,
        total_cost: 1500,
        executed_at: new Date().toISOString(),
        reasoning: 'Strong earnings report.'
    },
    {
        id: 't2',
        ticker: 'TSLA',
        signal: 'SELL',
        quantity: 5,
        price: 700,
        total_cost: 3500,
        executed_at: new Date().toISOString(),
        reasoning: 'Technical breakdown below support.'
    }
]

describe('TradesTable', () => {
    it('renders all trades in the list', () => {
        render(<TradesTable trades={mockTrades} />)
        expect(screen.getByText('AAPL')).toBeInTheDocument()
        expect(screen.getByText('TSLA')).toBeInTheDocument()
        expect(screen.getByText('BUY')).toBeInTheDocument()
        expect(screen.getByText('SELL')).toBeInTheDocument()
    })

    it('expands reasoning when a trade is clicked', () => {
        render(<TradesTable trades={mockTrades} />)

        // Reasoning hidden initially
        expect(screen.queryByText('Strong earnings report.')).not.toBeInTheDocument()

        // Click AAPL trade
        fireEvent.click(screen.getByText('AAPL'))

        expect(screen.getByText('Strong earnings report.')).toBeInTheDocument()
        expect(screen.getByText('Thinking Process')).toBeInTheDocument()
    })

    it('applies correct styling for signals', () => {
        render(<TradesTable trades={mockTrades} />)
        const buyBadge = screen.getByText('BUY')
        const sellBadge = screen.getByText('SELL')

        expect(buyBadge).toHaveClass('bg-emerald-50')
        expect(sellBadge).toHaveClass('bg-rose-50')
    })
})
