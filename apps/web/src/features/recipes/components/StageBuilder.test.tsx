import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { StageBuilder } from './StageBuilder';

describe('StageBuilder', () => {
    const stage = STARTER_RECIPES[0].stages[0];

    it('labels the card as the single LLM call and offers no remove control', () => {
        render(<StageBuilder stage={stage} onChange={vi.fn()} />);

        expect(screen.getByText('LLM Call')).toBeInTheDocument();
        expect(screen.queryByLabelText('LLM Call Title')).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Remove Stage' })).not.toBeInTheDocument();
    });

    it('emits an updated stage when a prompt block is added', () => {
        const onChange = vi.fn();
        render(<StageBuilder stage={stage} onChange={onChange} />);

        fireEvent.click(screen.getByRole('button', { name: '+ Prompt' }));

        expect(onChange).toHaveBeenCalledTimes(1);
        const updated = onChange.mock.calls[0][0];
        expect(updated.id).toBe(stage.id);
        expect(updated.blocks).toHaveLength(stage.blocks.length + 1);
        expect(updated.blocks.at(-1)).toEqual(expect.objectContaining({ type: 'prompt' }));
    });

    it('disables adding a second immutable output format block', () => {
        render(<StageBuilder stage={stage} onChange={vi.fn()} />);

        expect(screen.getByRole('button', { name: '+ Output Format' })).toBeDisabled();
    });

    it('cannot move the last content block down past the terminal block', () => {
        const twoBlockStage = {
            ...stage,
            blocks: [
                { id: 'only', type: 'prompt', text: 'Buy chips.' },
                { id: 'term', type: 'output_format' },
            ],
        } as unknown as typeof stage;
        const onChange = vi.fn();
        render(<StageBuilder stage={twoBlockStage} onChange={onChange} />);

        expect(screen.getByRole('button', { name: '↓' })).toBeDisabled();
    });
});
