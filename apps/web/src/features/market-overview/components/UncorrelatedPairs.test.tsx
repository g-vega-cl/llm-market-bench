import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { UncorrelatedPairs } from './UncorrelatedPairs';

describe('UncorrelatedPairs', () => {
    const mockCorrelationData = [
        {
            id: '1',
            run_id: 'run-1',
            ticker_a: 'XLK',
            ticker_b: 'XLE',
            pearson_corr: 0.15,
            spearman_corr: 0.12,
            returns_a_90d: 10.5,
            returns_b_90d: 5.2,
            data_points: 90,
        },
    ];

    it('renders the table headers with the selected timeframe (e.g., 30d)', () => {
        render(<UncorrelatedPairs correlationData={mockCorrelationData} timeframe="30d" />);

        // Check if the headers reflect the 30d timeframe
        expect(screen.getByText('30d Return A')).toBeInTheDocument();
        expect(screen.getByText('30d Return B')).toBeInTheDocument();

        // Check if the strategy note reflects the 30-day window
        expect(screen.getByText(/during the 30-day window/i)).toBeInTheDocument();
    });

    it('renders the table headers with the default 90d timeframe when not specified', () => {
        render(<UncorrelatedPairs correlationData={mockCorrelationData} />);

        expect(screen.getByText('90d Return A')).toBeInTheDocument();
        expect(screen.getByText('90d Return B')).toBeInTheDocument();
        expect(screen.getByText(/during the 90-day window/i)).toBeInTheDocument();
    });
});
