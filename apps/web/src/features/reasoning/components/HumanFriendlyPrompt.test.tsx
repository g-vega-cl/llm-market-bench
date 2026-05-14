import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { HumanFriendlyPrompt } from './HumanFriendlyPrompt';

describe('HumanFriendlyPrompt — uses design system', () => {
    it('role tab buttons use DS Button component', () => {
        const mockPrompt = [
            { role: 'system', content: 'test' },
            { role: 'user', content: 'hello' },
            { role: 'assistant', content: 'hi' },
            { role: 'tool', content: 'data' },
        ];
        render(<HumanFriendlyPrompt prompt={mockPrompt} />);

        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(4);

        for (const btn of buttons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });
});
