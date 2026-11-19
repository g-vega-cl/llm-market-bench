import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RecipePortfolioBlock } from './RecipePortfolioBlock';

describe('RecipePortfolioBlock', () => {
    it('renders empty 100% cash state when there are no open positions', () => {
        render(
            <RecipePortfolioBlock
                title="Current Portfolio & Open Positions"
                cash={10000}
                totalEquity={10000}
                openPositions={[]}
            />,
        );

        expect(screen.getByText('Current Portfolio & Open Positions')).toBeInTheDocument();
        expect(screen.getByText('0 / 4 Slots Open')).toBeInTheDocument();
        expect(screen.getByText('No open positions — 100% cash ($10,000.00).')).toBeInTheDocument();
    });

    it('renders open positions with mark price, market value, and signed unrealized P&L', () => {
        render(
            <RecipePortfolioBlock
                title="Current Portfolio & Open Positions"
                cash={5000}
                totalEquity={10250}
                openPositions={[
                    {
                        ticker: 'NVDA',
                        shares: 25,
                        entry_price: 200,
                        entry_time: '2026-08-04 09:30 ET',
                        cost_basis: 5000,
                        current_price: 210,
                        market_value: 5250,
                        unrealized_pnl_net: 250,
                        unrealized_return_pct: 5.0,
                    },
                    {
                        ticker: 'INTC',
                        shares: 10,
                        entry_price: 30,
                        entry_time: '2026-08-05 10:30 ET',
                        cost_basis: 300,
                        current_price: 27,
                        market_value: 270,
                        unrealized_pnl_net: -30,
                        unrealized_return_pct: -10.0,
                    },
                ]}
            />,
        );

        expect(screen.getByText('2 / 4 Slots Open')).toBeInTheDocument();
        expect(screen.getAllByText('$5,000.00').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('$10,250.00')).toBeInTheDocument();
        expect(screen.getByText('NVDA')).toBeInTheDocument();
        expect(screen.getByText('25')).toBeInTheDocument();
        expect(screen.queryByText('25.0000')).not.toBeInTheDocument();
        expect(screen.getByText('+$250.00')).toBeInTheDocument();
        expect(screen.getByText('+5.00%')).toBeInTheDocument();
        expect(screen.getByText('INTC')).toBeInTheDocument();
        expect(screen.getByText('-$30.00')).toBeInTheDocument();
        expect(screen.getByText('-10.00%')).toBeInTheDocument();
    });
});
