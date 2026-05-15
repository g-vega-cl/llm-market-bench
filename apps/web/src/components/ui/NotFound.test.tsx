import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { NotFound } from './NotFound';

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
        <a {...props}>{children}</a>
    ),
}));

describe('NotFound — uses design system', () => {
    it('renders "Go back" button using DS Button component', () => {
        render(<NotFound />);

        const button = screen.getByRole('button', { name: /go back/i });
        expect(button.className).toContain('inline-flex');
        expect(button.className).toContain('font-bold');
    });
});
