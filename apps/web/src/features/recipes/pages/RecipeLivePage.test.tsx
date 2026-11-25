import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { activateRecipeTurboFn } from '../api/recipes-quota-api';
import { livePageData } from './live-test-fixture';
import { RecipeLivePage } from './RecipeLivePage';

const mockNavigate = vi.fn();

function render(ui: React.ReactElement) {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return rtlRender(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

vi.mock('../api/recipes-quota-api', () => ({
    activateRecipeTurboFn: vi.fn(),
    fetchRecipeQuotaStatusFn: vi.fn(),
    toggleLiveScheduleFn: vi.fn(),
    switchLiveScheduleFn: vi.fn(),
}));

vi.mock('../api/recipes-api', () => ({
    enqueueRecipeJobFn: vi.fn(),
}));

vi.mock('../api/recipes-studio-api', () => ({
    submitWaitlistPledgeFn: vi.fn(),
}));

vi.mock('../api/fork-recipe', () => ({
    forkRecipeFn: vi.fn(),
}));

vi.mock('@tanstack/react-router', () => ({
    useNavigate: () => mockNavigate,
    Link: ({
        children,
        to,
        params,
        search,
        ...rest
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        search?: Record<string, string>;
        className?: string;
    }) => {
        let href = to;
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                href = href.replace(`$${k}`, v);
            }
        }
        if (search?.recipeId) {
            href = `${href}?recipeId=${search.recipeId}`;
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

describe('RecipeLivePage (hub)', () => {
    it('renders one card with the live summary strip and a single link into the run traces', () => {
        const { container } = render(
            <RecipeLivePage recipeId="rec-1" initialData={livePageData} />,
        );

        expect(container.querySelector('section[data-slot="scene-stage"]')).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Momentum Alpha');

        const strip = screen.getByTestId('bot-summary-strip');
        expect(strip).toHaveTextContent('Total Equity');
        expect(strip).toHaveTextContent('$10,250.00');
        expect(strip).toHaveTextContent('$10,000.00');
        expect(strip).toHaveTextContent('1 / 4');
        expect(strip).toHaveTextContent(/Apr 6 • 11:32 AM ET/);

        expect(
            screen.getByRole('link', { name: /Run traces, portfolio & closed trades/i }),
        ).toHaveAttribute('href', '/recipes/live/rec-1/runs');

        // Hub serves one purpose: traces, portfolio and closed trades moved out.
        expect(screen.queryByText(/Live Run Traces/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Live Paper Portfolio/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/All Closed Live Trades/i)).not.toBeInTheDocument();
    });

    it('renders empty-state placeholders with no live state', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={null} />);

        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Live Runs · rec-1/i);
        const strip = screen.getByTestId('bot-summary-strip');
        expect(strip).toHaveTextContent('—');
        expect(screen.queryByText(/Live Paper Portfolio/i)).not.toBeInTheDocument();
    });

    it('links to Overview and Blueprint in the shared sub-nav', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={livePageData} />);

        expect(screen.getByRole('link', { name: 'Overview' })).toHaveAttribute(
            'href',
            '/recipes/rec-1',
        );
        expect(screen.getByRole('link', { name: 'Live Runs' })).toHaveAttribute(
            'aria-current',
            'page',
        );
        expect(screen.getByRole('link', { name: 'Blueprint' })).toHaveAttribute(
            'href',
            '/recipes/rec-1/edit',
        );
    });

    describe('Next run schedule label & Turbo (America/New_York)', () => {
        afterEach(() => {
            vi.useRealTimers();
        });

        it('shows 16:00 ET today at 15:50 EST on a Wednesday', () => {
            vi.useFakeTimers();
            vi.setSystemTime(new Date('2026-11-18T15:50:00-05:00'));

            render(<RecipeLivePage recipeId="rec-1" initialData={null} />);

            expect(screen.getByText(/Next run: 16:00 ET today/i)).toBeInTheDocument();
        });

        it('shows 09:30 ET tomorrow at 16:05 EST on a Wednesday', () => {
            vi.useFakeTimers();
            vi.setSystemTime(new Date('2026-11-18T16:05:00-05:00'));

            render(<RecipeLivePage recipeId="rec-1" initialData={null} />);

            expect(screen.getByText(/Next run: 09:30 ET tomorrow/i)).toBeInTheDocument();
        });

        it('shows 12:30 ET today at 12:00 EST on a Wednesday', () => {
            vi.useFakeTimers();
            vi.setSystemTime(new Date('2026-11-18T12:00:00-05:00'));

            render(<RecipeLivePage recipeId="rec-1" initialData={null} />);

            expect(screen.getByText(/Next run: 12:30 ET today/i)).toBeInTheDocument();
        });

        it('shows 09:30 ET Monday on Friday after 16:00 EST', () => {
            vi.useFakeTimers();
            vi.setSystemTime(new Date('2026-11-20T16:05:00-05:00'));

            render(<RecipeLivePage recipeId="rec-1" initialData={null} />);

            expect(screen.getByText(/Next run: 09:30 ET Monday/i)).toBeInTheDocument();
        });

        it('shows 09:30 ET Monday on Saturday', () => {
            vi.useFakeTimers();
            vi.setSystemTime(new Date('2026-11-21T11:00:00-05:00'));

            render(<RecipeLivePage recipeId="rec-1" initialData={null} />);

            expect(screen.getByText(/Next run: 09:30 ET Monday/i)).toBeInTheDocument();
        });

        it('activates Turbo for owner during market hours and shows countdown', async () => {
            vi.useFakeTimers({ shouldAdvanceTime: true });
            vi.setSystemTime(new Date('2026-11-18T11:00:00-05:00'));
            vi.mocked(activateRecipeTurboFn).mockResolvedValue({
                recipeId: 'rec-1',
                turboExpiresAt: '2026-11-18T12:00:00-05:00',
                enqueuedJobId: 'job-turbo-1',
            });

            render(<RecipeLivePage recipeId="rec-1" initialData={livePageData} />);

            fireEvent.click(screen.getByRole('button', { name: /Turbo \(5m x 1h\)/i }));

            await waitFor(() => {
                expect(activateRecipeTurboFn).toHaveBeenCalledWith({ data: { recipeId: 'rec-1' } });
                expect(
                    screen.getByRole('button', { name: /Turbo: 60m left \(5m\)/i }),
                ).toBeDisabled();
            });
        });

        it('renders Live: PAUSED when liveMeta.isLive is false', () => {
            render(
                <RecipeLivePage
                    recipeId="rec-1"
                    initialData={{
                        ...livePageData,
                        liveMeta: {
                            recipeName: 'Momentum',
                            isLive: false,
                            isOwner: true,
                            turboExpiresAt: null,
                            turboUsedToday: false,
                        },
                    }}
                />,
            );

            expect(screen.getByText('Live: PAUSED')).toBeInTheDocument();
            expect(screen.getByText(/Next run: Paused/)).toBeInTheDocument();
            expect(screen.queryByText(/Live: ON/i)).not.toBeInTheDocument();
        });

        it('disables Turbo button when market is closed', () => {
            vi.useFakeTimers();
            vi.setSystemTime(new Date('2026-11-21T11:00:00-05:00'));

            render(<RecipeLivePage recipeId="rec-1" initialData={livePageData} />);

            expect(screen.getByRole('button', { name: /Turbo \(Market Closed\)/i })).toBeDisabled();
        });
    });
});
