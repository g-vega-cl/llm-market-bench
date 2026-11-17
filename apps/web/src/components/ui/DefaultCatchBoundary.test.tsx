import { render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
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
            state: { location: { pathname: '/portfolios', href: '/portfolios' } },
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

    it('captures error in PostHog with route context and metadata', async () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const testErr = new Error('Database connection failed');
        render(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);

        await waitFor(() => {
            expect(mockCaptureException).toHaveBeenCalledTimes(1);
        });
        expect(mockCaptureException).toHaveBeenCalledWith(testErr, {
            source: 'DefaultCatchBoundary',
            is_root: false,
            pathname: '/',
            route_id: '/portfolios',
        });
        warnSpy.mockRestore();
    });

    it('deduplicates consecutive captures for the exact same error instance', async () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const testErr = new Error('Persistent render error');
        const { rerender } = render(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);

        await waitFor(() => {
            expect(mockCaptureException).toHaveBeenCalledTimes(1);
        });
        expect(warnSpy).toHaveBeenCalledTimes(1);
        expect(errorSpy).not.toHaveBeenCalled();

        // Re-render with identical error reference
        rerender(<DefaultCatchBoundary error={testErr} reset={vi.fn()} />);
        await new Promise((resolve) => setTimeout(resolve, 20));
        expect(mockCaptureException).toHaveBeenCalledTimes(1);
        expect(warnSpy).toHaveBeenCalledTimes(1);

        // Re-render with new error instance
        const nextErr = new Error('Different error');
        rerender(<DefaultCatchBoundary error={nextErr} reset={vi.fn()} />);
        await waitFor(() => {
            expect(mockCaptureException).toHaveBeenCalledTimes(2);
        });
        expect(warnSpy).toHaveBeenCalledTimes(2);
        expect(errorSpy).not.toHaveBeenCalled();
        warnSpy.mockRestore();
        errorSpy.mockRestore();
    });

    it('normalizes string errors into Error instances for PostHog', async () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        render(
            <DefaultCatchBoundary error={'Network timeout' as unknown as Error} reset={vi.fn()} />,
        );

        await waitFor(() => {
            expect(mockCaptureException).toHaveBeenCalledTimes(1);
        });
        const capturedErr = mockCaptureException.mock.calls[0][0];
        expect(capturedErr).toBeInstanceOf(Error);
        expect(capturedErr.message).toBe('Network timeout');
        warnSpy.mockRestore();
    });

    it('triggers bounded chunk reload under StrictMode and captures exception before reload', async () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const reloadSpy = vi.fn();
        const originalLocation = window.location;
        const fakeLocation = {
            ...originalLocation,
            origin: 'https://www.benchify.dev',
            pathname: '/portfolios',
            search: '',
            href: 'https://www.benchify.dev/portfolios',
            reload: reloadSpy,
        };
        Object.defineProperty(window, 'location', {
            configurable: true,
            value: fakeLocation,
        });
        sessionStorage.clear();

        try {
            const chunkErr = new TypeError(
                'error loading dynamically imported module: https://www.benchify.dev/assets/recipes-demo-gg4vQRPg.js',
            );

            const { rerender } = render(
                <StrictMode>
                    <DefaultCatchBoundary error={chunkErr} reset={vi.fn()} />
                </StrictMode>,
            );

            expect(screen.getByText(/Checking application update/i)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /reload page/i })).toBeInTheDocument();

            await waitFor(() => {
                expect(reloadSpy).toHaveBeenCalledTimes(1);
            });
            expect(screen.getByText(/Updating application to latest version/i)).toBeInTheDocument();
            expect(mockCaptureException).toHaveBeenCalledTimes(1);
            expect(mockCaptureException).toHaveBeenCalledWith(
                chunkErr,
                expect.objectContaining({
                    source: 'DefaultCatchBoundary',
                    is_root: false,
                    pathname: '/portfolios',
                    route_id: '/portfolios',
                    chunk_error: true,
                    auto_reloaded: true,
                }),
            );

            // Rerendering the same boundary with a new chunk error within cooldown hits circuit breaker
            const chunkErr2 = new TypeError(
                'Failed to fetch dynamically imported module: https://www.benchify.dev/assets/recipes-demo-gg4vQRPg.js',
            );
            rerender(
                <StrictMode>
                    <DefaultCatchBoundary error={chunkErr2} reset={vi.fn()} />
                </StrictMode>,
            );

            await waitFor(() => {
                expect(
                    screen.getByText(
                        /Unable to load the latest application update\. Please reload the page\./i,
                    ),
                ).toBeInTheDocument();
                expect(mockCaptureException).toHaveBeenCalledTimes(2);
            });
            expect(reloadSpy).toHaveBeenCalledTimes(1);
            expect(mockCaptureException).toHaveBeenLastCalledWith(
                chunkErr2,
                expect.objectContaining({
                    source: 'DefaultCatchBoundary',
                    chunk_error: true,
                    auto_reloaded: false,
                }),
            );
        } finally {
            Object.defineProperty(window, 'location', {
                configurable: true,
                value: originalLocation,
            });
            sessionStorage.clear();
            warnSpy.mockRestore();
        }
    });

    it('falls back to console.error when PostHog captureException is unavailable', async () => {
        mockUsePostHog.mockReturnValue(undefined as never);
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const err = new Error('PostHog unavailable');

        render(<DefaultCatchBoundary error={err} reset={vi.fn()} />);

        await waitFor(() => {
            expect(errorSpy).toHaveBeenCalledWith(err);
        });
        expect(mockCaptureException).not.toHaveBeenCalled();
        expect(warnSpy).not.toHaveBeenCalled();
        errorSpy.mockRestore();
        warnSpy.mockRestore();
    });
});
