import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ThoughtProcessFlow } from './ThoughtProcessFlow';

describe('ThoughtProcessFlow — uses design system', () => {
    it('step tab buttons use DS Button component', () => {
        render(<ThoughtProcessFlow />);

        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(5);

        for (const btn of buttons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });
});
