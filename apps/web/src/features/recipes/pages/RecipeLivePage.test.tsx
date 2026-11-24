import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { activateRecipeTurboFn } from '../api/recipes-quota-api';
import type { LivePortfolioAndRuns } from '../types';
import { RecipeLivePage } from './RecipeLivePage';

function render(ui: React.ReactElement) {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return rtlRender(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

vi.mock('../api/recipes-quota-api', () => ({
    activateRecipeTurboFn: vi.fn(),
}));

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        search,
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        search?: Record<string, string>;
        className?: string;
    }) => <a href={search?.recipeId ? `${to}?recipeId=${search.recipeId}` : to}>{children}</a>,
}));

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
            status: 'completed',
            progress_pct: 100,
            provider: 'free-llm-proxy',
            model: 'auto-go',
            result_json: {
                mode: 'live_turn',
                as_of_utc: '2026-04-06T09:30:00Z',
                slot_label: '2026-04-06T09:30',
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
        {
            id: 'job-2',
            recipe_id: 'rec-1',
            mode: 'live_turn',
            status: 'pending',
            progress_pct: 0,
            provider: 'free-llm-proxy',
            model: 'auto-go',
            result_json: null,
            error_message: null,
            created_at: '2026-04-06T12:32:00Z',
        },
    ],
};

describe('RecipeLivePage', () => {
    it('renders empty state when no live state is available', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={null} />);

        expect(screen.getByRole('heading', { name: /Live Status/i })).toBeInTheDocument();
        expect(screen.getByText(/Recipe ID: rec-1/i)).toBeInTheDocument();
        expect(screen.getByText(/No live runs yet/i)).toBeInTheDocument();
        expect(screen.queryByText(/Live Paper Portfolio/i)).not.toBeInTheDocument();
    });

    it('renders live paper portfolio and the selected run trace', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

        expect(screen.getByRole('heading', { name: /Live Status/i })).toBeInTheDocument();
        expect(screen.getByText(/Live Paper Portfolio/i)).toBeInTheDocument();
        expect(screen.getByText(/Cash Available/i)).toBeInTheDocument();
        expect(screen.getByText(/Total Equity/i)).toBeInTheDocument();
        expect(screen.getAllByText(/NVDA/i).length).toBeGreaterThan(0);

        expect(screen.getByText(/Live Run Traces/i)).toBeInTheDocument();
        expect(screen.getByText(/LLM Call/i)).toBeInTheDocument();
        expect(screen.getByText(/Analyze NVDA at slot 1/i)).toBeInTheDocument();
        expect(screen.getAllByText(/BUY NVDA/i).length).toBeGreaterThan(0);
    });

    it('renders run selector with all persisted runs', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

        // Both jobs appear in the RunSelectorBar with their created_at stamps in ET.
        expect(screen.getByText(/Apr 6 • 5:32 AM ET/i)).toBeInTheDocument();
        expect(screen.getByText(/Apr 6 • 8:32 AM ET/i)).toBeInTheDocument();
    });

    it('switches run selection and surfaces a pending run without trace output', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

        fireEvent.click(screen.getByText(/Apr 6 • 8:32 AM ET/i));

        expect(screen.getByText(/Selected live job has no trace output yet/i)).toBeInTheDocument();
        expect(screen.queryByText(/Analyze NVDA at slot 1/i)).not.toBeInTheDocument();
    });

    it('links back to the builder with the active recipeId', () => {
        render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

        expect(screen.getByRole('link', { name: /Edit Bot/i })).toHaveAttribute(
            'href',
            '/build?recipeId=rec-1',
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

            render(
                <RecipeLivePage
                    recipeId="rec-1"
                    initialData={{
                        ...initialData,
                        liveMeta: {
                            recipeName: 'Momentum',
                            isLive: true,
                            isOwner: true,
                            turboExpiresAt: null,
                            turboUsedToday: false,
                        },
                    }}
                />,
            );

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
            expect(screen.getByText('Next run: Paused')).toBeInTheDocument();
            expect(screen.queryByText(/Live: ON/i)).not.toBeInTheDocument();
        });

        it('disables Turbo button when market is closed', () => {
            vi.useFakeTimers();
            vi.setSystemTime(new Date('2026-11-21T11:00:00-05:00'));

            render(
                <RecipeLivePage
                    recipeId="rec-1"
                    initialData={{
                        ...initialData,
                        liveMeta: {
                            recipeName: 'Momentum',
                            isLive: true,
                            isOwner: true,
                            turboExpiresAt: null,
                            turboUsedToday: false,
                        },
                    }}
                />,
            );

            expect(screen.getByRole('button', { name: /Turbo \(Market Closed\)/i })).toBeDisabled();
        });
    });

    describe('Portfolio Equity & Benchmark Chart', () => {
        const dataWithCurve: LivePortfolioAndRuns = {
            ...initialData,
            portfolio: {
                ...initialData.portfolio,
                equity_curve: [
                    { time: '2026-11-14 09:30 ET', equity: 10000 },
                    { time: '2026-11-18 15:30 ET', equity: 10500 },
                ],
            },
        };

        it('shows empty equity history message when equity_curve is empty', () => {
            render(<RecipeLivePage recipeId="rec-1" initialData={initialData} />);

            expect(screen.getByText(/Portfolio Equity & Benchmark/i)).toBeInTheDocument();
            expect(screen.getByText(/No equity history available yet/i)).toBeInTheDocument();
        });

        it('defaults to SPY benchmark comparison and allows switching to other benchmarks or None', async () => {
            const benchmarkFetchFn = vi.fn(
                async (
                    tickers: string[],
                ): Promise<Record<string, { date: string; price: number }[]>> => {
                    if (tickers[0] === 'SPY') {
                        return {
                            SPY: [
                                { date: '2026-11-14', price: 500 },
                                { date: '2026-11-18', price: 510 },
                            ],
                        };
                    }
                    if (tickers[0] === 'QQQ') {
                        return {
                            QQQ: [
                                { date: '2026-11-14', price: 400 },
                                { date: '2026-11-18', price: 416 },
                            ],
                        };
                    }
                    return {};
                },
            );

            render(
                <RecipeLivePage
                    recipeId="rec-1"
                    initialData={dataWithCurve}
                    benchmarkFetchFn={benchmarkFetchFn}
                />,
            );

            await waitFor(() => {
                expect(benchmarkFetchFn).toHaveBeenCalledWith(['SPY'], '2026-11-14', '2026-11-18');
                expect(screen.getByText(/Performance vs Benchmark/i)).toBeInTheDocument();
            });
            expect(screen.getByText(/S&P 500:/i)).toBeInTheDocument();
            expect(screen.getByText(/\+3\.00% outperformance/i)).toBeInTheDocument();

            const select = screen.getByLabelText(/Benchmark/i);
            fireEvent.change(select, { target: { value: 'QQQ' } });

            await waitFor(() => {
                expect(benchmarkFetchFn).toHaveBeenCalledWith(['QQQ'], '2026-11-14', '2026-11-18');
                expect(screen.getByText(/Nasdaq 100:/i)).toBeInTheDocument();
            });

            fireEvent.change(select, { target: { value: '' } });
            await waitFor(() => {
                expect(screen.getByText(/Equity Curve/i)).toBeInTheDocument();
                expect(screen.getByText('$10,500.00')).toBeInTheDocument();
            });
        });

        it('shows Day 1 benchmark notice and skips benchmark fetch for single-day curves', () => {
            const benchmarkFetchFn = vi.fn();
            const singleDayData: LivePortfolioAndRuns = {
                ...initialData,
                portfolio: {
                    ...initialData.portfolio,
                    equity_curve: [
                        { time: '2026-11-24 09:30 ET', equity: 10000 },
                        { time: '2026-11-24 14:30 ET', equity: 10150 },
                    ],
                },
            };

            render(
                <RecipeLivePage
                    recipeId="rec-1"
                    initialData={singleDayData}
                    benchmarkFetchFn={benchmarkFetchFn}
                />,
            );

            expect(screen.getByText(/Benchmark comparison begins on Day 2/i)).toBeInTheDocument();
            expect(benchmarkFetchFn).not.toHaveBeenCalled();
            expect(screen.getByText('$10,150.00')).toBeInTheDocument();
        });
    });
});
