import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { LeaderboardRow } from '../api/portfolio-leaderboard';
import { TopPortfolios } from './TopPortfolios';

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

const rows: LeaderboardRow[] = [
    { portfolioId: 'a', label: 'Max Pain', returnPct: 2.31, observations: 19, series: [] },
    { portfolioId: 'b', label: 'Daily SPY', returnPct: -0.42, observations: 20, series: [] },
];

describe('TopPortfolios', () => {
    it('lists each ranked portfolio with its return', () => {
        render(<TopPortfolios rows={rows} trackedCount={28} windowDays={30} />);

        expect(screen.getByText('Max Pain')).toBeInTheDocument();
        expect(screen.getByText('+2.31%')).toBeInTheDocument();
        expect(screen.getByText('-0.42%')).toBeInTheDocument();
        expect(screen.getByText(/28 portfolios/)).toBeInTheDocument();
    });

    it('links to the full board and the recipe gallery', () => {
        render(<TopPortfolios rows={rows} trackedCount={28} windowDays={30} />);

        expect(screen.getByText('See all portfolios').closest('a')).toHaveAttribute(
            'href',
            '/portfolios',
        );
        expect(screen.getByText('Need inspiration?').closest('a')).toHaveAttribute(
            'href',
            '/recipes',
        );
    });

    it('renders an empty state before the first close', () => {
        render(<TopPortfolios rows={[]} trackedCount={0} windowDays={30} />);

        expect(screen.getByText(/board fills after the next close/i)).toBeInTheDocument();
    });
});
