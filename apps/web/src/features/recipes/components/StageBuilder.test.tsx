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

    it('pins the single prompt block first, disables + Prompt, and inserts added data blocks before output_format', () => {
        const onChange = vi.fn();
        render(<StageBuilder stage={stage} onChange={onChange} />);

        expect(screen.getByRole('button', { name: '+ Prompt' })).toBeDisabled();
        expect(screen.getByText('PINNED FIRST')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: '+ News' }));

        expect(onChange).toHaveBeenCalledTimes(1);
        const updated = onChange.mock.calls[0][0];
        expect(updated.id).toBe(stage.id);
        expect(updated.blocks).toHaveLength(stage.blocks.length + 1);
        expect(updated.blocks[0]).toEqual(expect.objectContaining({ type: 'prompt' }));
        expect(updated.blocks.at(-1)).toEqual(expect.objectContaining({ type: 'output_format' }));
        expect(updated.blocks.at(-2)).toEqual(expect.objectContaining({ type: 'news' }));
    });

    it('preserves trailing spaces and newlines while editing the pinned prompt block', () => {
        const onChange = vi.fn();
        render(<StageBuilder stage={stage} onChange={onChange} />);

        const textarea = screen.getByLabelText('Prompt text');
        fireEvent.change(textarea, { target: { value: 'Buy NVDA \nwith RSI < 60 ' } });

        expect(onChange).toHaveBeenCalledTimes(1);
        const updated = onChange.mock.calls[0][0];
        expect(updated.blocks[0]).toEqual(
            expect.objectContaining({ type: 'prompt', text: 'Buy NVDA \nwith RSI < 60 ' }),
        );
    });

    it('disables adding a second immutable output format block', () => {
        render(<StageBuilder stage={stage} onChange={vi.fn()} />);

        expect(screen.getByRole('button', { name: '+ Output Format' })).toBeDisabled();
    });
});
