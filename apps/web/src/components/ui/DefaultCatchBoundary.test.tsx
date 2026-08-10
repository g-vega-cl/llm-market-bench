import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DefaultCatchBoundary } from './DefaultCatchBoundary';

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        ErrorComponent: ({ error }: { error?: Error }) => (
            <div>Error: {error?.message || 'Unknown error'}</div>
        ),
        Link: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
            <a {...props}>{children}</a>
        ),
        useRouter: () => ({ invalidate: vi.fn() }),
        useMatch: () => false,
        rootRouteId: '__root__',
    };
});

describe('DefaultCatchBoundary — uses design system', () => {
    it('renders "Try Again" button using DS Button component', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        render(<DefaultCatchBoundary error={new Error('test error')} reset={vi.fn()} />);

        const button = screen.getByRole('button', { name: /try again/i });
        expect(button.className).toContain('inline-flex');
        expect(button.className).toContain('font-bold');
        consoleSpy.mockRestore();
    });
});
