import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScoreCalculation } from './ScoreCalculation';

describe('ScoreCalculation', () => {
    it('renders the formula correctly', () => {
        render(<ScoreCalculation />);
        expect(screen.getByText(/0\.4 × \(Portfolio% - SPY%\)/i)).toBeInTheDocument();
        expect(screen.getByText(/0\.4 × \(Portfolio% - Do-Nothing%\)/i)).toBeInTheDocument();
        expect(screen.getByText(/0\.2 × \(Portfolio% - 10Y Bond%\)/i)).toBeInTheDocument();
        expect(screen.getByText(/Max Drawdown% × 0.3/i)).toBeInTheDocument();
    });

    it('renders the explanation sections', () => {
        render(<ScoreCalculation />);
        expect(screen.getByRole('heading', { name: /^Excess Return$/i })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /^Risk-Free Excess$/i })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /^Risk Penalty$/i })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /^The "Ratchet"$/i })).toBeInTheDocument();
    });
});
