import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DefaultCatchBoundary } from './DefaultCatchBoundary';

const mockCaptureException = vi.fn();

const mockUsePostHog = vi.fn(() => ({
    captureException: mockCaptureException,
}));

vi.mock('@posthog/react', () => ({
    usePostHog: () => mockUsePostHog(),
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
        mockUsePostHog.mockReturnValue({ captureException: mockCaptureException });
    });

    it('renders "Try Again" button using DS Button component', () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        render(<DefaultCatchBoundary error={new Error('test error')} reset={vi.fn()} />);

        const button = screen.getByRole('button', { name: /try again/i });
        expect(button.className).toContain('inline-flex');
        expect(button.className).toContain('font-bold');
        warnSpy.mockRestore();
    });

    it('captures error in PostHog with route context and metadata', () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const testErr = new Error('Database connection failed');
        render(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);

        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        expect(mockCaptureException).toHaveBeenCalledWith(testErr, {
            source: 'DefaultCatchBoundary',
            is_root: false,
            pathname: '/',
            route_id: '/portfolios',
        });
        warnSpy.mockRestore();
    });

    it('deduplicates consecutive captures for the exact same error instance', () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const testErr = new Error('Persistent render error');
        const { rerender } = render(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);

        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        expect(warnSpy).toHaveBeenCalledTimes(1);
        expect(errorSpy).not.toHaveBeenCalled();

        // Re-render with identical error reference
        rerender(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);
        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        expect(warnSpy).toHaveBeenCalledTimes(1);

        // Re-render with new error instance
        const nextErr = new Error('Different error');
        rerender(<DefaultCatchBoundary error={nextErr} reset={vi.fn()} />);
        expect(mockCaptureException).toHaveBeenCalledTimes(2);
        expect(warnSpy).toHaveBeenCalledTimes(2);
        expect(errorSpy).not.toHaveBeenCalled();
        warnSpy.mockRestore();
        errorSpy.mockRestore();
    });

    it('normalizes string errors into Error instances for PostHog', () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        render(
            <DefaultCatchBoundary error={'Network timeout' as unknown as Error} reset={vi.fn()} />,
        );

        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        const capturedErr = mockCaptureException.mock.calls[0][0];
        expect(capturedErr).toBeInstanceOf(Error);
        expect(capturedErr.message).toBe('Network timeout');
        warnSpy.mockRestore();
    });

    it('renders ErrorComponent and captures exception directly when chunk failure occurs', () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const chunkErr = new TypeError(
            'Failed to fetch dynamically imported module: https://www.benchify.dev/assets/index-CZJZmMUs.js',
        );

        render(<DefaultCatchBoundary error={chunkErr} reset={vi.fn()} />);

        // Should render ErrorComponent and Try Again button cleanly without disruptive reload banners
        expect(
            screen.getByText(/Failed to fetch dynamically imported module/i),
        ).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();

        // Should capture exception with full context directly to PostHog
        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        expect(mockCaptureException).toHaveBeenCalledWith(
            chunkErr,
            expect.objectContaining({
                source: 'DefaultCatchBoundary',
                is_root: false,
                pathname: '/',
                route_id: '/portfolios',
            }),
        );
        warnSpy.mockRestore();
    });

    it('falls back to console.error when PostHog captureException is unavailable', () => {
        mockUsePostHog.mockReturnValue(undefined as never);
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const err = new Error('PostHog unavailable');

        render(<DefaultCatchBoundary error={err} reset={vi.fn()} />);

        expect(mockCaptureException).not.toHaveBeenCalled();
        expect(errorSpy).toHaveBeenCalledWith(err);
        expect(warnSpy).not.toHaveBeenCalled();
        errorSpy.mockRestore();
        warnSpy.mockRestore();
    });
});
