import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BuilderAlignmentCard } from './BuilderAlignmentCard';
import type { AlignmentQuestion } from './compiler';

const questions: AlignmentQuestion[] = [
    {
        id: 'q1',
        question: 'Which sector?',
        recommended: 1,
        options: ['Cloud', 'Semis', 'Energy', 'Banks'],
    },
    {
        id: 'q2',
        question: 'Exit rule?',
        recommended: 1,
        options: ['Thesis break', 'RSI > 80'],
    },
];

function renderCard(
    onSubmit = vi.fn(),
    overrides: Partial<{ questions: AlignmentQuestion[] }> = {},
) {
    render(
        <BuilderAlignmentCard
            questions={overrides.questions ?? questions}
            isCompiling={false}
            onSubmit={onSubmit}
            onSkip={vi.fn()}
        />,
    );
    return onSubmit;
}

describe('BuilderAlignmentCard', () => {
    it('pins every card, two-option rows included, to the same height and width grid', () => {
        renderCard();

        const row = screen.getByTestId('alignment-options-1');
        expect(row).toHaveClass('grid', 'grid-cols-2', 'sm:grid-cols-4', 'gap-2', 'items-stretch');
        expect(row).not.toHaveClass('flex-wrap');

        for (const button of within(row).getAllByRole('button')) {
            expect(button).toHaveClass('h-14', 'w-full', 'min-w-0');
        }
        for (const button of within(screen.getByTestId('alignment-options-2')).getAllByRole(
            'button',
        )) {
            expect(button).toHaveClass('h-14', 'w-full', 'min-w-0');
        }
    });

    it('groups each option row under its question', () => {
        renderCard();

        const group = screen.getByRole('group', { name: /Which sector\?/ });
        expect(group).toBe(screen.getByTestId('alignment-question-1'));
        expect(within(group).getAllByRole('button')).toHaveLength(4);
    });

    it('leads with the recommended option and marks it with an R badge', () => {
        renderCard();

        const row = screen.getByTestId('alignment-options-1');
        const [first, ...rest] = within(row).getAllByRole('button');
        // The visible label stays inside the accessible name (WCAG 2.5.3).
        expect(first).toHaveAccessibleName(/^Cloud, recommended$/);
        expect(within(first).getByText('R')).toBeInTheDocument();
        expect(within(first).getByText(', recommended')).toHaveClass('sr-only');
        for (const button of rest) {
            expect(within(button).queryByText('R')).toBeNull();
            expect(button).not.toHaveAccessibleName(/recommended/);
        }

        // Nothing explains a bare letter, so the card carries its own legend.
        expect(screen.getByText('R = our pick')).toBeInTheDocument();
    });

    it('marks exactly one card even if the index is unusable', () => {
        renderCard(vi.fn(), {
            questions: [
                {
                    id: 'q1',
                    question: 'Which sector?',
                    recommended: 9,
                    options: ['Cloud', 'Semis'],
                },
            ],
        });

        const [first, second] = within(screen.getByTestId('alignment-options-1')).getAllByRole(
            'button',
        );
        expect(within(first).getByText('R')).toBeInTheDocument();
        expect(within(second).queryByText('R')).toBeNull();
    });

    it('keeps the badge readable when the marked card is selected', () => {
        renderCard();

        const recommended = within(screen.getByTestId('alignment-options-1')).getAllByRole(
            'button',
        )[0];
        const badge = within(recommended).getByText('R');
        expect(badge).toHaveClass('bg-accent', 'text-voxel-trough');

        fireEvent.click(recommended);
        expect(recommended).toHaveAttribute('aria-pressed', 'true');
        // Same fill as the solid button would erase the badge box.
        expect(badge).toHaveClass('bg-voxel-trough', 'text-accent');
        expect(within(recommended).getByText('R')).toBeInTheDocument();
    });

    it('selects the recommended card like any other option and submits its text', () => {
        const onSubmit = renderCard();

        const recommended = within(screen.getByTestId('alignment-options-1')).getAllByRole(
            'button',
        )[0];
        expect(recommended).toHaveAttribute('aria-pressed', 'false');

        fireEvent.click(recommended);
        expect(recommended).toHaveAttribute('aria-pressed', 'true');

        fireEvent.click(
            within(screen.getByTestId('alignment-options-2')).getAllByRole('button')[0],
        );
        fireEvent.click(screen.getByRole('button', { name: /build final bot/i }));

        expect(onSubmit).toHaveBeenCalledWith([
            { question: 'Which sector?', answer: 'Cloud' },
            { question: 'Exit rule?', answer: 'Thesis break' },
        ]);
    });

    it('does not pre-select the recommendation on mount', () => {
        renderCard();

        const optionButtons = [
            ...within(screen.getByTestId('alignment-options-1')).getAllByRole('button'),
            ...within(screen.getByTestId('alignment-options-2')).getAllByRole('button'),
        ];
        expect(optionButtons).toHaveLength(6);
        for (const button of optionButtons) {
            expect(button).toHaveAttribute('aria-pressed', 'false');
        }
        expect(screen.getByRole('button', { name: /build final bot/i })).toBeDisabled();
    });
});
