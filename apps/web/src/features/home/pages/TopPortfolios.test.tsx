import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { EquityPoint, LeaderboardRow } from '../api/portfolio-leaderboard';
import { TopPortfolios } from './TopPortfolios';

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

const series = (values: number[]): EquityPoint[] =>
    values.map((value, index) => ({
        date: `2026-11-${String(10 + index).padStart(2, '0')}`,
        value,
    }));

const rows: LeaderboardRow[] = [
    {
        portfolioId: 'a',
        label: 'Max Pain',
        returnPct: 2.31,
        observations: 3,
        series: series([0, 1, 2.31]),
    },
    {
        portfolioId: 'b',
        label: 'Daily SPY',
        returnPct: -0.42,
        observations: 3,
        series: series([0, -0.2, -0.42]),
    },
];

const worst: LeaderboardRow = {
    portfolioId: 'c',
    label: 'Thesis Fader',
    returnPct: -6.1,
    observations: 3,
    series: series([0, -3, -6.1]),
};

const spy = series([0, 0.3, 0.53]);

describe('TopPortfolios', () => {
    it('gives every portfolio its own lane instead of one shared frame', () => {
        const { container } = render(
            <TopPortfolios rows={rows} trackedCount={28} windowDays={30} />,
        );

        // Two ranked rows plus one sparkline each: no six-line overlay.
        expect(container.querySelectorAll('figure li')).toHaveLength(2);
        expect(container.querySelectorAll('svg title').length).toBe(2);
    });

    it('lists each ranked portfolio with its return', () => {
        render(<TopPortfolios rows={rows} trackedCount={28} windowDays={30} />);

        expect(screen.getByText('Max Pain')).toBeInTheDocument();
        expect(screen.getByText('+2.31%')).toBeInTheDocument();
        expect(screen.getByText('-0.42%')).toBeInTheDocument();
        expect(screen.getByText(/28 portfolios/)).toBeInTheDocument();
    });

    it('publishes the loser under the winners', () => {
        const { container } = render(
            <TopPortfolios rows={rows} worst={worst} trackedCount={28} windowDays={30} />,
        );

        expect(screen.getByText('Thesis Fader')).toBeInTheDocument();
        expect(screen.getByText('-6.10%')).toBeInTheDocument();
        expect(container.textContent).toContain('Lowest of 28');
    });

    it('draws the benchmark in its own row, dashed and muted', () => {
        const { container } = render(
            <TopPortfolios rows={rows} spy={spy} trackedCount={28} windowDays={30} />,
        );

        expect(screen.getByText('SPY (benchmark)')).toBeInTheDocument();
        const dashed = container.querySelector('polyline.stroke-voxel-muted');
        expect(dashed).not.toBeNull();
    });

    it('labels each sparkline for screen readers', () => {
        render(<TopPortfolios rows={rows} trackedCount={28} windowDays={30} />);

        expect(screen.getByText('Max Pain, 3 sessions')).toBeInTheDocument();
    });

    it('shows the board median beside the count', () => {
        render(
            <TopPortfolios rows={rows} medianReturnPct={-2.55} trackedCount={28} windowDays={30} />,
        );

        expect(screen.getByText(/median -2\.55%/)).toBeInTheDocument();
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

        expect(screen.getByText(/fills after the next close/i)).toBeInTheDocument();
    });
});
