import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScoreCalculation } from './ScoreCalculation';

describe('ScoreCalculation', () => {
    it('renders the formula correctly', () => {
        render(<ScoreCalculation />);
        expect(screen.getByText(/Portfolio% - SPY%/i)).toBeInTheDocument();
        expect(screen.getByText(/Max Drawdown% × 0.3/i)).toBeInTheDocument();
    });

    it('renders the explanation sections', () => {
        render(<ScoreCalculation />);
        expect(screen.getByText(/Excess Return/i)).toBeInTheDocument();
        expect(screen.getByText(/Risk Penalty/i)).toBeInTheDocument();
        expect(screen.getByText(/The "Ratchet"/i)).toBeInTheDocument();
    });
});
