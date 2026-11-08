import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ConsolePortfolioStrip } from './ConsolePortfolioStrip';

describe('ConsolePortfolioStrip', () => {
    it('returns null when portfolio is undefined', () => {
        const { container } = render(<ConsolePortfolioStrip portfolio={undefined} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders 100% cash state when no shares held', () => {
        render(
            <ConsolePortfolioStrip
                portfolio={{
                    total_equity: 10000,
                    cash_balance: 10000,
                    position_shares: 0,
                    position_cost_basis: 0,
                    position_market_value: 0,
                    unrealized_pnl: 0,
                    realized_pnl: 0,
                }}
            />,
        );

        expect(screen.getByTestId('console-portfolio-strip')).toBeInTheDocument();
        expect(screen.getByText('Live Desk Portfolio')).toBeInTheDocument();
        expect(screen.getByText('$10,000.00')).toBeInTheDocument();
        expect(screen.getByText('0 SPY (100% Cash)')).toBeInTheDocument();
    });

    it('renders active SPY position with allocation percentage and positive PnL', () => {
        render(
            <ConsolePortfolioStrip
                portfolio={{
                    total_equity: 10100,
                    cash_balance: 8080,
                    position_shares: 4,
                    position_cost_basis: 500,
                    position_market_value: 2020,
                    unrealized_pnl: 20,
                    realized_pnl: 0,
                }}
            />,
        );

        expect(screen.getByText('$10,100.00')).toBeInTheDocument();
        expect(screen.getByText('4 SPY (20.0% alloc)')).toBeInTheDocument();
        expect(screen.getByText('+$20.00 (+1.00%)')).toBeInTheDocument();
    });
});
