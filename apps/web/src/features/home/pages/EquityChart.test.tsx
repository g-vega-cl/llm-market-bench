import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { LeaderboardRow } from '../api/portfolio-leaderboard';
import { EquityChart } from './EquityChart';

const row = (id: string, label: string, returnPct: number): LeaderboardRow => ({
    portfolioId: id,
    label,
    returnPct,
    observations: 19,
    series: [
        { date: '2026-11-10', value: 0 },
        { date: '2026-11-19', value: returnPct },
    ],
});

const spy = [
    { date: '2026-11-10', value: 0 },
    { date: '2026-11-19', value: 1.2 },
];

describe('EquityChart', () => {
    it('draws one line per portfolio plus the SPY baseline', () => {
        const { container } = render(
            <EquityChart
                rows={[row('a', 'Max Pain', 2.3), row('b', 'Daily SPY', 1.1)]}
                spy={spy}
            />,
        );

        // one SPY polyline + two portfolio polylines
        expect(container.querySelectorAll('polyline')).toHaveLength(3);
        expect(container.querySelectorAll('polyline')[0].getAttribute('stroke-dasharray')).toBe(
            '6 4',
        );
    });

    it('exposes an accessible description', () => {
        render(<EquityChart rows={[row('a', 'Max Pain', 2.3)]} spy={spy} />);

        expect(screen.getByRole('img', { name: /equity curves/i })).toBeInTheDocument();
    });

    it('labels each line with its name and the axis range', () => {
        const { container } = render(
            <EquityChart
                rows={[row('a', 'Max Pain', 2.3), row('b', 'Daily SPY', -0.4)]}
                spy={spy}
            />,
        );

        expect(screen.getByText('Max Pain')).toBeInTheDocument();
        expect(screen.getByText('Daily SPY')).toBeInTheDocument();
        // The caption is built from several interpolations, so match the text content.
        expect(container.textContent).toContain('SPY dashed · Nov 10 to Nov 19');
    });

    it('skips series with a single observation and shows the empty state when nothing is plottable', () => {
        const single: LeaderboardRow = {
            ...row('c', 'One Day', 0.5),
            series: [{ date: '2026-11-19', value: 0.5 }],
        };

        render(<EquityChart rows={[single]} spy={spy} />);

        expect(screen.getByText(/equity curves appear after the first close/i)).toBeInTheDocument();
    });
});
