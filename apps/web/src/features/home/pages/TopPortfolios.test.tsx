import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { EquityPoint, LeaderboardRow } from '../api/portfolio-leaderboard';
import { TopPortfolios } from './TopPortfolios';

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        className?: string;
    }) => {
        const href = params
            ? Object.entries(params).reduce(
                  (acc, [key, value]) => acc.replace(`$${key}`, value),
                  to,
              )
            : to;
        return (
            <a href={href} className={className}>
                {children}
            </a>
        );
    },
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

    it('links ranked and worst portfolio rows to their receipt pages, leaving SPY and blank IDs non-linked', () => {
        render(
            <TopPortfolios
                rows={[
                    ...rows,
                    {
                        portfolioId: '   ',
                        label: 'Skewed Row',
                        returnPct: 0.1,
                        observations: 2,
                        series: series([0, 0.1]),
                    },
                ]}
                worst={worst}
                spy={spy}
                trackedCount={28}
                windowDays={30}
            />,
        );

        expect(screen.getByText('Max Pain').closest('a')).toHaveAttribute('href', '/portfolios/a');
        expect(screen.getByText('Thesis Fader').closest('a')).toHaveAttribute(
            'href',
            '/portfolios/c',
        );
        expect(screen.getByText('Skewed Row').closest('a')).toBeNull();
        expect(screen.getByText('SPY (benchmark)').closest('a')).toBeNull();
    });

    it('links to the full board and the reasoning logs', () => {
        render(<TopPortfolios rows={rows} trackedCount={28} windowDays={30} />);

        expect(screen.getByText('See all portfolios').closest('a')).toHaveAttribute(
            'href',
            '/portfolios',
        );
        expect(screen.getByText('Read reasoning logs').closest('a')).toHaveAttribute(
            'href',
            '/reasoning',
        );
    });

    it('lays the two calls to action on an equal-width grid', () => {
        render(<TopPortfolios rows={rows} trackedCount={28} windowDays={30} />);

        const ctaGrid = screen.getByText('See all portfolios').closest('a')?.parentElement;
        expect(ctaGrid?.className).toContain('grid');

        for (const label of ['See all portfolios', 'Read reasoning logs']) {
            const link = screen.getByText(label).closest('a');
            expect(link?.className).toContain('w-full');
            expect(link?.className).toContain('justify-center');
        }
    });

    it('renders an empty state before the first close', () => {
        render(<TopPortfolios rows={[]} trackedCount={0} windowDays={30} />);

        expect(screen.getByText(/fills after the next close/i)).toBeInTheDocument();
    });
});
