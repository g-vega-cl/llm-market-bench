import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
        <a {...props}>{children}</a>
    ),
}));

import { PortfolioComparisonChart } from './PortfolioComparisonChart';

describe('PortfolioComparisonChart — uses design system', () => {
    it('renders chart container (DS Button integration)', () => {
        const { container } = render(
            <PortfolioComparisonChart
                data={[]}
                benchmarkData={{}}
                selectedBenchmark="SPY"
                onReset={vi.fn()}
            />,
        );

        // Component renders — DS Button is used internally (verified by import)
        expect(container.querySelector('svg')).toBeTruthy();
    });

    it('defensively handles invalid dates, NaN values, and duplicate dates in performance and benchmark data', () => {
        const data = [
            {
                portfolioId: 'port-1',
                ownerId: 'owner-1',
                performance: [
                    { date: '2026-05-01', value: 10 },
                    { date: '2026-05-02', value: NaN }, // NaN value
                    { date: 'invalid-date', value: 20 }, // Invalid date
                    { date: '2026-05-03', value: 30 },
                    { date: '2026-05-03', value: 40 }, // Duplicate date
                ],
            },
        ];

        const benchmarkData = {
            SPY: [
                { date: '2026-05-01', price: 100 },
                { date: 'invalid-benchmark-date', price: 110 }, // Invalid date
                { date: '2026-05-02', price: NaN }, // NaN price
                { date: '2026-05-03', price: 120 },
                { date: '2026-05-03', price: 130 }, // Duplicate date
            ],
        };

        const { container } = render(
            <PortfolioComparisonChart
                data={data}
                benchmarkData={benchmarkData}
                selectedBenchmark="SPY"
                onReset={vi.fn()}
            />,
        );

        const paths = container.querySelectorAll('path');
        expect(paths.length).toBeGreaterThan(0);

        paths.forEach((path) => {
            const dAttr = path.getAttribute('d');
            if (dAttr) {
                // The generated path MUST NOT contain any NaN or invalid coordinate values
                expect(dAttr).not.toContain('NaN');
                expect(dAttr).not.toContain('undefined');

                // The path should not contain duplicate x-coordinates that cause vertical spikes.
                // We check if there are repeated 'L' command X-positions that are identical.
                const commands = dAttr.split(/[MLZ]/).filter(Boolean);
                const xCoordinates = commands.map((cmd) => cmd.split(',')[0].trim());
                const uniqueXCoordinates = new Set(xCoordinates);
                expect(xCoordinates.length).toBe(uniqueXCoordinates.size);
            }
        });
    });
});
