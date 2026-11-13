import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { StageBuilder } from './StageBuilder';

describe('StageBuilder', () => {
    const stage = STARTER_RECIPES[0].stages[0];

    it('labels the card as the single LLM call and offers no remove control', () => {
        render(<StageBuilder stage={stage} onChange={vi.fn()} />);

        expect(screen.getByText('LLM Call')).toBeInTheDocument();
        expect(screen.getByLabelText('LLM Call Title')).toHaveValue(stage.title);
        expect(screen.queryByRole('button', { name: 'Remove Stage' })).not.toBeInTheDocument();
    });

    it('disables adding a second immutable output format block', () => {
        render(<StageBuilder stage={stage} onChange={vi.fn()} />);

        expect(screen.getByRole('button', { name: '+ Output Format' })).toBeDisabled();
    });

    it('reports title edits as an updated stage', () => {
        const onChange = vi.fn();
        render(<StageBuilder stage={stage} onChange={onChange} />);

        fireEvent.change(screen.getByLabelText('LLM Call Title'), {
            target: { value: 'Momentum' },
        });

        expect(onChange).toHaveBeenLastCalledWith(
            expect.objectContaining({ id: stage.id, title: 'Momentum' }),
        );
    });
});
