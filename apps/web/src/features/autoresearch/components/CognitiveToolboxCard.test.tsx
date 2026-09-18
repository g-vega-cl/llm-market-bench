import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CognitiveToolboxCard } from './CognitiveToolboxCard';

describe('CognitiveToolboxCard', () => {
    it('renders empty fallback message when no tools are selected', () => {
        render(<CognitiveToolboxCard selectedTools={[]} />);
        expect(screen.getByText('0 Tools')).toBeInTheDocument();
        expect(
            screen.getByText('No specific cognitive tools were configured for this experiment.'),
        ).toBeInTheDocument();
    });

    it('renders enabled tools count and catalog badges', () => {
        render(
            <CognitiveToolboxCard
                selectedTools={['get_stock_quote', 'get_portfolio_ledger']}
                parentSelectedTools={['get_stock_quote']}
            />,
        );

        expect(screen.getByText(/2 \/ \d+ Tools Enabled/)).toBeInTheDocument();
        expect(screen.getByText('get_portfolio_ledger')).toBeInTheDocument();
        expect(screen.getByText('+ get_portfolio_ledger')).toBeInTheDocument();
    });
});
