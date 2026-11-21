import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { PublicSpotlight } from '~/features/recipes/api/public-board-api';
import { BuildProof } from './BuildProof';

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        className?: string;
    }) => (
        <a href={to} className={className}>
            {children}
        </a>
    ),
}));

const spotlight: PublicSpotlight = {
    recipeId: 'r-new',
    name: 'Chip Momentum',
    prompt: 'Buy chipmakers when AI capex news turns positive',
    blocks: ['Prompt', 'News', 'Output'],
    returnPct: 3.2,
    spyReturnPct: 1.1,
};

describe('BuildProof', () => {
    it('shows the sentence, the compiled blocks and the result', () => {
        render(<BuildProof spotlight={spotlight} onFork={vi.fn()} />);

        expect(screen.getByText(/chipmakers when AI capex/i)).toBeInTheDocument();
        expect(screen.getByText('Prompt')).toBeInTheDocument();
        expect(screen.getByText('News')).toBeInTheDocument();
        expect(screen.getByText('Output')).toBeInTheDocument();
        expect(screen.getByText(/\+3\.20% vs SPY \+1\.10%/)).toBeInTheDocument();
    });

    it('forks the bot the panel is showing', () => {
        const onFork = vi.fn();
        render(<BuildProof spotlight={spotlight} onFork={onFork} />);

        fireEvent.click(screen.getByText('Fork this bot'));

        expect(onFork).toHaveBeenCalledWith('r-new');
    });

    it('exposes a public backtest receipt link with or without a spotlight and wraps text rows cleanly', () => {
        const { rerender } = render(<BuildProof spotlight={spotlight} onFork={vi.fn()} />);
        const sampleLink = screen.getByText(/See a sample backtest/i).closest('a');
        expect(sampleLink).toHaveAttribute('href', '/recipes-demo');
        expect(sampleLink?.className).toContain('whitespace-nowrap');
        expect(sampleLink?.parentElement?.className).toContain('flex-wrap');

        rerender(<BuildProof spotlight={null} onFork={vi.fn()} />);
        expect(screen.getByText(/No public bot has a written prompt yet/i)).toBeInTheDocument();
        expect(screen.queryByText('Fork this bot')).not.toBeInTheDocument();
        const fallbackLink = screen.getByText(/See a sample backtest/i).closest('a');
        expect(fallbackLink).toHaveAttribute('href', '/recipes-demo');
        expect(fallbackLink?.className).toContain('whitespace-nowrap');
    });
});
