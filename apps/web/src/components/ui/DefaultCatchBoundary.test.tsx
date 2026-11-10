import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DefaultCatchBoundary } from './DefaultCatchBoundary';

const mockCaptureException = vi.fn();

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        captureException: mockCaptureException,
    }),
}));

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
        useRouter: () => ({
            invalidate: vi.fn(),
            state: { location: { pathname: '/portfolios' } },
        }),
        useMatch: () => false,
        rootRouteId: '__root__',
    };
});

describe('DefaultCatchBoundary', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders "Try Again" button using DS Button component', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        render(<DefaultCatchBoundary error={new Error('test error')} reset={vi.fn()} />);

        const button = screen.getByRole('button', { name: /try again/i });
        expect(button.className).toContain('inline-flex');
        expect(button.className).toContain('font-bold');
        consoleSpy.mockRestore();
    });

    it('captures error in PostHog with route context and metadata', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const testErr = new Error('Database connection failed');
        render(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);

        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        expect(mockCaptureException).toHaveBeenCalledWith(testErr, {
            source: 'DefaultCatchBoundary',
            is_root: false,
            pathname: '/',
            route_id: '/portfolios',
            chunk_error: false,
            auto_reloaded: false,
        });
        consoleSpy.mockRestore();
    });

    it('deduplicates consecutive captures for the exact same error instance', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const testErr = new Error('Persistent render error');
        const { rerender } = render(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);

        expect(mockCaptureException).toHaveBeenCalledTimes(1);

        // Re-render with identical error reference
        rerender(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);
        expect(mockCaptureException).toHaveBeenCalledTimes(1);

        // Re-render with new error instance
        const nextErr = new Error('Different error');
        rerender(<DefaultCatchBoundary error={nextErr} reset={vi.fn()} />);
        expect(mockCaptureException).toHaveBeenCalledTimes(2);
        consoleSpy.mockRestore();
    });

    it('normalizes string errors into Error instances for PostHog', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        render(
            <DefaultCatchBoundary error={'Network timeout' as unknown as Error} reset={vi.fn()} />,
        );

        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        const capturedErr = mockCaptureException.mock.calls[0][0];
        expect(capturedErr).toBeInstanceOf(Error);
        expect(capturedErr.message).toBe('Network timeout');
        consoleSpy.mockRestore();
    });

    it('detects dynamic import chunk failures and triggers auto-reload with updating UI', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const chunkErr = new TypeError(
            'Failed to fetch dynamically imported module: https://www.benchify.dev/assets/index-CZJZmMUs.js',
        );

        render(<DefaultCatchBoundary error={chunkErr} reset={vi.fn()} />);

        // Should render smooth updating UI instead of generic error
        expect(screen.getByText(/updating application to latest version/i)).toBeInTheDocument();
        expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();

        // Should capture exception with auto_reloaded flag
        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        expect(mockCaptureException).toHaveBeenCalledWith(
            chunkErr,
            expect.objectContaining({
                source: 'DefaultCatchBoundary',
                chunk_error: true,
            }),
        );
        consoleSpy.mockRestore();
    });
});
