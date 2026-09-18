import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PromptBlocksCard } from './PromptBlocksCard';

describe('PromptBlocksCard', () => {
    it('returns null when selectedBlocks is empty', () => {
        const { container } = render(<PromptBlocksCard selectedBlocks={[]} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders active blocks, descriptions, and pivot delta', () => {
        render(
            <PromptBlocksCard
                selectedBlocks={['let_winners_run', 'cut_losers_fast']}
                parentSelectedBlocks={['let_winners_run']}
            />,
        );

        expect(screen.getByText('Modular Reasoning & Discipline Blocks')).toBeInTheDocument();
        expect(screen.getByText(/2 \/ \d+ Blocks Active/)).toBeInTheDocument();
        expect(screen.getByText('LET WINNERS RUN')).toBeInTheDocument();
        expect(screen.getByText('CUT LOSERS FAST')).toBeInTheDocument();
        expect(screen.getByText('+ cut_losers_fast')).toBeInTheDocument();
    });
});
