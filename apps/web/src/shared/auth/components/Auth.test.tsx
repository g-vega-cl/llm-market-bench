import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Auth } from './Auth';

vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: () => ({
        auth: {
            signInWithOAuth: vi.fn(),
        },
    }),
}));

describe('Auth — uses design system', () => {
    const defaultProps = {
        actionText: 'Login',
        onSubmit: vi.fn(),
        status: 'idle' as const,
    };

    it('renders buttons using DS Button component', () => {
        render(<Auth {...defaultProps} />);

        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(1);

        // DS Button renders with these base classes
        for (const btn of buttons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });

    it('renders inputs using DS Input component', () => {
        render(<Auth {...defaultProps} />);

        // DS Input wraps in a div with these classes, then has the input inside
        const inputWrapper = screen.getByLabelText('Username').closest('div');
        expect(inputWrapper?.className).toContain('rounded-xl');
        expect(inputWrapper?.className).toContain('border');
    });

    it('renders labels using DS Label component', () => {
        render(<Auth {...defaultProps} />);

        const labels = screen.getAllByText(/Username|Password/);
        expect(labels.length).toBe(2);

        // DS Label renders with these classes
        for (const label of labels) {
            expect(label.className).toContain('font-semibold');
            expect(label.className).toContain('text-zinc-700');
        }
    });
});
