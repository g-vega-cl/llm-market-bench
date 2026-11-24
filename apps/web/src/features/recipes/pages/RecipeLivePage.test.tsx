import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { activateRecipeTurboFn } from '../api/recipes-quota-api';
import type { LivePortfolioAndRuns } from '../types';
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

const initialData: LivePortfolioAndRuns = {
    portfolio: {
        cash: 10000,
        total_equity: 10250,
        open_positions: [
            {
                ticker: 'NVDA',
                shares: 2,
                entry_price: 120,
                entry_time: '2026-04-06T09:30:00Z',
                current_price: 135,
                market_value: 270,
                cost_basis: 240,
                unrealized_pnl_net: 30,
                unrealized_return_pct: 12.5,
            },
        ],
        trades: [],
    },
    recentLiveRuns: [
        {
            id: 'job-1',
            recipe_id: 'rec-1',
            mode: 'live_turn',
            status: 'pending',
            progress_pct: 0,
            provider: 'free-llm-proxy',
            model: 'auto-go',
            result_json: null,
            error_message: null,
            created_at: '2026-04-06T15:32:00Z',
        },
        {
            id: 'job-2',
            recipe_id: 'rec-1',
            mode: 'live_turn',
            status: 'completed',
            progress_pct: 100,
            provider: 'free-llm-proxy',
            model: 'auto-go',
            result_json: {
                mode: 'live_turn',
                as_of_utc: '2026-04-06T12:00:00Z',
                stages: [
                    {
                        stage_id: 's1',
                        prompt: 'Analyze MSFT at slot 2.',
                        output: 'HOLD',
                        tool_calls: [],
                        trace: { rounds: [], forced_final_synthesis: false },
                    },
                ],
                final_output: '[]',
                signals: [],
            },
            error_message: null,
            created_at: '2026-04-06T12:32:00Z',
            started_at: '2026-04-06T12:32:00Z',
            completed_at: '2026-04-06T12:32:05Z',
        },
        {
            id: 'job-3',
            recipe_id: 'rec-1',
            mode: 'live_turn',
            status: 'completed',
            progress_pct: 100,
            provider: 'free-llm-proxy',
            model: 'auto-go',
            result_json: {
                mode: 'live_turn',
                as_of_utc: '2026-04-06T09:30:00Z',
                slot_label: 'SLOT-LABEL-RAW',
                stages: [
                    {
                        stage_id: 's1',
                        prompt: 'Analyze NVDA at slot 1.',
                        output: 'BUY NVDA',
                        tool_calls: [],
                        trace: { rounds: [], forced_final_synthesis: false },
                    },
                ],
                final_output: '[{"action":"BUY","ticker":"NVDA"}]',
                signals: [{ action: 'BUY', ticker: 'NVDA' }],
            },
            error_message: null,
            created_at: '2026-04-06T09:32:00Z',
            started_at: '2026-04-06T09:32:00Z',
            completed_at: '2026-04-06T09:32:05Z',
        },
    ],
    liveMeta: {
        recipeName: 'Momentum Alpha',
        isLive: true,
        isOwner: true,
        turboExpiresAt: null,
        turboUsedToday: false,
    },
};

describe('RecipeLivePage', () => {
    it('renders empty state inside the living SceneStage header when no live state is available', () => {
        const { container } = render(<RecipeLivePage recipeId="rec-1" initialData={null} />);

        expect(container.querySelector('section[data-slot="scene-stage"]')).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Live Runs · rec-1/i);
        expect(screen.getByText(/No live runs yet/i)).toBeInTheDocument();
        expect(screen.queryByText(/Live Paper Portfolio/i)).not.toBeInTheDocument();
    });

    it('renders live paper portfolio, closed trades section, and the trace of the run being viewed', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

        expect(screen.getByRole('heading', { name: 'Momentum Alpha' })).toBeInTheDocument();
        expect(screen.getByText(/Live Paper Portfolio/i)).toBeInTheDocument();
        expect(screen.getByText(/All Closed Live Trades/i)).toBeInTheDocument();
        expect(screen.getAllByText(/NVDA/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/Live Run Traces/i)).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Older' }));
        fireEvent.click(screen.getByRole('button', { name: 'Older' }));

        expect(screen.getByText('LLM Call')).toBeInTheDocument();
        expect(screen.getByText(/Analyze NVDA at slot 1/i)).toBeInTheDocument();
        expect(screen.getAllByText(/BUY NVDA/i).length).toBeGreaterThan(0);
    });

    it('lands on the newest run and swaps the mounted trace when paging older', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

        expect(screen.queryByText(/Recent Live Turns/i)).not.toBeInTheDocument();
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
        render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

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
        const withFailure: typeof initialData = {
            ...initialData,
            recentLiveRuns: [
                {
                    ...initialData.recentLiveRuns[0],
                    status: 'failed',
                    error_message: 'LLM timeout',
                },
                ...initialData.recentLiveRuns.slice(1),
            ],
        };
        render(<RecipeLivePage recipeId="rec-1" initialData={withFailure} />);

        expect(screen.getByText(/failed — no trace output/i)).toBeInTheDocument();
        expect(screen.queryByText(/no trace output yet/i)).not.toBeInTheDocument();
        expect(screen.getByText('LLM timeout')).toBeInTheDocument();
    });

    it('links to Overview and Blueprint in the shared BotStageHeader sub-nav', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

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

            render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

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
                        ...initialData,
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

            render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

            expect(screen.getByRole('button', { name: /Turbo \(Market Closed\)/i })).toBeDisabled();
        });
    });
});
