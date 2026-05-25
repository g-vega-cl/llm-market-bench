import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { VolatilityCalculation } from './VolatilityCalculation';

describe('VolatilityCalculation', () => {
    it('renders with active experiment state (missing metrics)', () => {
        const mockExperiment = {} as PromptExperiment;

        render(<VolatilityCalculation experiment={mockExperiment} />);

        expect(screen.getByText('Volatility Methodology')).toBeInTheDocument();
        expect(
            screen.getByText(/This experiment variant is currently active/i),
        ).toBeInTheDocument();
    });

    it('renders with finalized metrics and shows correct calculations', () => {
        const mockExperiment = {
            metrics: {
                volatility: 15.8745, // 15.87% annualized volatility
            },
        } as unknown as PromptExperiment;

        render(<VolatilityCalculation experiment={mockExperiment} />);

        expect(screen.getByText('Volatility Methodology')).toBeInTheDocument();

        // 15.8745% / sqrt(252) approx 1.00%
        expect(screen.getByText('15.87%')).toBeInTheDocument();
        expect(screen.getByText('1.0000%')).toBeInTheDocument();

        // Check if formula elements are present
        expect(screen.getByText(/Annualization Factor/i)).toBeInTheDocument();
        expect(screen.getAllByText(/√252/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/Equal-Weighted Daily Returns/i)).toBeInTheDocument();
    });
});
