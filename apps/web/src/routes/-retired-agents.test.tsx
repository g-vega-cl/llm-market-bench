import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RetiredAgentsView } from './retired-agents';

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        Link: ({
            to,
            params,
            children,
            className,
        }: {
            to: string;
            params?: Record<string, string>;
            children: React.ReactNode;
            className?: string;
        }) => {
            const href = params?.portfolioId ? to.replace('$portfolioId', params.portfolioId) : to;
            return (
                <a href={href} className={className}>
                    {children}
                </a>
            );
        },
    };
});

const retired = [
    {
        id: 'ret-1',
        owner_id: 'gemini-3.1-pro-preview',
        cash_balance: 45000,
        buying_power: 45000,
        total_equity: 98500,
        last_updated_at: '2026-01-01',
        excess_liquidity: 45000,
        maintenance_margin: 0,
        realized: 0,
        sma: 45000,
    },
];

describe('RetiredAgentsView (/retired-agents)', () => {
    it('lists each retired agent linking to its portfolio', () => {
        render(<RetiredAgentsView retiredPortfolios={retired} />);
        const link = screen.getByText('gemini-3.1-pro-preview').closest('a');
        expect(link).toHaveAttribute('href', '/portfolios/ret-1');
        expect(screen.getByText('$98,500')).toBeInTheDocument();
    });

    it('shows an empty state when there are no retired agents', () => {
        render(<RetiredAgentsView retiredPortfolios={[]} />);
        expect(screen.getByText('No retired agents.')).toBeInTheDocument();
    });
});
