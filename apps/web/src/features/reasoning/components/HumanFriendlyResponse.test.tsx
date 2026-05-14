import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { HumanFriendlyResponse } from './HumanFriendlyResponse';

describe('HumanFriendlyResponse — uses design system', () => {
    it('tab buttons use DS Button component', () => {
        const mockResponse = { analysis: 'test', confidence: 0.9 };
        render(<HumanFriendlyResponse response={mockResponse} />);

        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(2);

        for (const btn of buttons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });

    it('renders raw JSON copy button using DS Button when response is not an object', () => {
        render(<HumanFriendlyResponse response="not an object" />);

        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(1);

        for (const btn of buttons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });
});
