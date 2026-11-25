import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render as rtlRender, screen } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { livePageData } from './live-test-fixture';
import { RecipeLiveRunsPage } from './RecipeLiveRunsPage';

function render(ui: React.ReactElement) {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return rtlRender(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
        ...rest
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        className?: string;
    }) => {
        let href = to;
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                href = href.replace(`$${k}`, v);
            }
        }
        return (
            <a href={href} {...rest}>
                {children}
            </a>
        );
    },
}));

beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: true,
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    });

    if (typeof globalThis.ResizeObserver === 'undefined') {
        globalThis.ResizeObserver = class ResizeObserver {
            observe() {}
            unobserve() {}
            disconnect() {}
        };
    }
});

describe('RecipeLiveRunsPage (detail)', () => {
    it('carries the back link and a chip row that claims this URL', () => {
        render(<RecipeLiveRunsPage recipeId="rec-1" initialData={livePageData} />);

        expect(
            screen.getByRole('link', { name: /Back to Momentum Alpha Overview/i }),
        ).toHaveAttribute('href', '/recipes/rec-1');
        expect(screen.getByRole('link', { name: 'Live Runs' })).toHaveAttribute(
            'aria-current',
            'page',
        );
    });

    it('renders the trace of the run being viewed and leaves the portfolio to Performance', () => {
        render(<RecipeLiveRunsPage recipeId="rec-1" initialData={livePageData} />);

        expect(screen.getByText(/Live Run Traces/i)).toBeInTheDocument();
        expect(screen.queryByText(/Live Paper Portfolio/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/All Closed Live Trades/i)).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Older' }));
        fireEvent.click(screen.getByRole('button', { name: 'Older' }));

        expect(screen.getByText('LLM Call')).toBeInTheDocument();
        expect(screen.getByText(/Analyze NVDA at slot 1/i)).toBeInTheDocument();
        expect(screen.getAllByText(/BUY NVDA/i).length).toBeGreaterThan(0);
    });

    it('lands on the newest run and swaps the mounted trace when paging older', () => {
        render(<RecipeLiveRunsPage recipeId="rec-1" initialData={livePageData} />);

        expect(screen.getByRole('status')).toHaveTextContent('1 of 3');
        expect(screen.getByText(/Apr 6 • 11:32 AM ET/)).toBeInTheDocument();
        expect(screen.getByText(/no trace output yet/i)).toBeInTheDocument();
        expect(screen.queryByText(/Analyze MSFT at slot 2/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Analyze NVDA at slot 1/i)).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Newer' })).toHaveAttribute(
            'aria-disabled',
            'true',
        );

        fireEvent.click(screen.getByRole('button', { name: 'Older' }));

        expect(screen.getByRole('status')).toHaveTextContent('2 of 3');
        expect(screen.getByText(/Apr 6 • 8:00 AM ET/)).toBeInTheDocument();
        expect(screen.getByText(/Analyze MSFT at slot 2/i)).toBeInTheDocument();
        expect(screen.queryByText(/no trace output yet/i)).not.toBeInTheDocument();
    });

    it('walks to the oldest run, names it in the trace header, and stops at the end', () => {
        render(<RecipeLiveRunsPage recipeId="rec-1" initialData={livePageData} />);

        fireEvent.click(screen.getByRole('button', { name: 'Older' }));
        fireEvent.click(screen.getByRole('button', { name: 'Older' }));

        expect(screen.getByRole('status')).toHaveTextContent('3 of 3');
        expect(screen.getByText(/Apr 6 • 5:30 AM ET/)).toBeInTheDocument();
        expect(screen.queryByText(/SLOT-LABEL-RAW/)).not.toBeInTheDocument();
        expect(screen.getByText(/Analyze NVDA at slot 1/i)).toBeInTheDocument();
        expect(screen.queryByText(/Analyze MSFT at slot 2/i)).not.toBeInTheDocument();

        const older = screen.getByRole('button', { name: 'Older' });
        expect(older).toHaveAttribute('aria-disabled', 'true');
        expect(older).not.toBeDisabled();
        older.focus();
        fireEvent.click(older);
        expect(document.activeElement).toBe(older);
        expect(screen.getByRole('status')).toHaveTextContent('3 of 3');

        fireEvent.click(screen.getByRole('button', { name: 'Newer' }));
        expect(screen.getByRole('status')).toHaveTextContent('2 of 3');
        expect(screen.getByText(/Analyze MSFT at slot 2/i)).toBeInTheDocument();
    });

    it('surfaces a failed run as terminal rather than "yet", with its error', () => {
        const withFailure = {
            ...livePageData,
            recentLiveRuns: [
                {
                    ...livePageData.recentLiveRuns[0],
                    status: 'failed' as const,
                    error_message: 'LLM timeout',
                },
                ...livePageData.recentLiveRuns.slice(1),
            ],
        };
        render(<RecipeLiveRunsPage recipeId="rec-1" initialData={withFailure} />);

        expect(screen.getByText(/failed — no trace output/i)).toBeInTheDocument();
        expect(screen.queryByText(/no trace output yet/i)).not.toBeInTheDocument();
        expect(screen.getByText('LLM timeout')).toBeInTheDocument();
    });

    it('shows the empty trace state when the bot has never run', () => {
        render(
            <RecipeLiveRunsPage
                recipeId="rec-1"
                initialData={{ ...livePageData, recentLiveRuns: [] }}
            />,
        );

        expect(screen.getByText(/No live runs yet/i)).toBeInTheDocument();
    });
});
