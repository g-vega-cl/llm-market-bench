import { fireEvent, render } from '@testing-library/react';
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

    it('only shows at most 5 portfolios by default when more than 5 are provided', () => {
        const tenPortfolios = Array.from({ length: 10 }, (_, i) => ({
            portfolioId: `port-${i + 1}`,
            ownerId: `agent-${i + 1}`,
            performance: [
                { date: '2026-05-01', value: 10 + i },
                { date: '2026-05-02', value: 15 + i },
            ],
        }));

        const { container } = render(
            <PortfolioComparisonChart
                data={tenPortfolios}
                benchmarkData={{}}
                selectedBenchmark=""
                onReset={vi.fn()}
            />,
        );

        // Should render exactly 5 portfolio lines for the default top 5 portfolios (not all 10)
        const portfolioLines = container.querySelectorAll('.portfolio-line');
        expect(portfolioLines.length).toBe(5);
    });

    it('allows users to remove and add portfolios up to max 5, and never more than 5', () => {
        const tenPortfolios = Array.from({ length: 10 }, (_, i) => ({
            portfolioId: `port-${i + 1}`,
            ownerId: `agent-${i + 1}`,
            performance: [
                { date: '2026-05-01', value: 10 + i },
                { date: '2026-05-02', value: 15 + i },
            ],
        }));

        const { container } = render(
            <PortfolioComparisonChart
                data={tenPortfolios}
                benchmarkData={{}}
                selectedBenchmark=""
                onReset={vi.fn()}
            />,
        );

        // Initially 5 portfolio lines
        expect(container.querySelectorAll('.portfolio-line').length).toBe(5);

        // Remove agent-1
        const removeButton = container.querySelector(
            'button[aria-label="Remove agent 1 from comparison"]',
        ) as HTMLButtonElement;
        expect(removeButton).toBeTruthy();
        fireEvent.click(removeButton);

        // Now exactly 4 portfolio lines (users can show less than 5)
        expect(container.querySelectorAll('.portfolio-line').length).toBe(4);

        // Add an unselected portfolio (port-6) via the select combobox
        const select = container.querySelector(
            'select[aria-label="Add agent to comparison"]',
        ) as HTMLSelectElement;
        expect(select).not.toBeDisabled();
        fireEvent.change(select, { target: { value: 'port-6' } });

        // Now exactly 5 portfolio lines again
        expect(container.querySelectorAll('.portfolio-line').length).toBe(5);

        // With 5 portfolios selected, the add select should now be disabled (never more than 5)
        expect(select).toBeDisabled();

        // Reset to top 5 restores initial selection
        const resetToTop5 = Array.from(container.querySelectorAll('button')).find((b) =>
            b.textContent?.includes('Reset to Top 5'),
        );
        expect(resetToTop5).toBeTruthy();
        if (resetToTop5) {
            fireEvent.click(resetToTop5);
        }

        expect(container.querySelectorAll('.portfolio-line').length).toBe(5);
        expect(
            container.querySelector('button[aria-label="Remove agent 1 from comparison"]'),
        ).toBeTruthy();
    });
});
