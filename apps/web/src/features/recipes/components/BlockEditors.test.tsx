import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PromptBlockEditor } from './BlockEditors';

describe('PromptBlockEditor', () => {
    it('uses the single-call placeholder and reports edits', () => {
        const onUpdate = vi.fn();
        render(
            <PromptBlockEditor
                block={{ id: 'blk-p', type: 'prompt', text: '' }}
                onUpdate={onUpdate}
            />,
        );

        const textarea = screen.getByLabelText('Prompt text');
        expect(textarea).toHaveAttribute('placeholder', 'Write instructions for the LLM...');

        fireEvent.change(textarea, { target: { value: 'Find momentum' } });
        expect(onUpdate).toHaveBeenCalledWith('Find momentum');
    });
});
