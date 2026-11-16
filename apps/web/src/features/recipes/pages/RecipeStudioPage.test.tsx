import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { fetchRecipeQuotaStatusFn, toggleLiveScheduleFn } from '../api/recipes-quota-api';
import { fetchLivePortfolioAndRunsFn } from '../api/recipes-studio-api';
import * as liveStudioHelpers from '../utils/live-studio-helpers';
import { RecipeStudioPage } from './RecipeStudioPage';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        className?: string;
    }) => {
        const href = params
            ? Object.entries(params).reduce((acc, [key, val]) => acc.replace(`$${key}`, val), to)
            : to;
        return (
            <a href={href} className={className}>
                {children}
            </a>
        );
    },
    useNavigate: () => mockNavigate,
}));

vi.mock('../api/recipes-api', () => ({
    enqueueRecipeJobFn: vi.fn(),
    getRecipeJobStatusFn: vi.fn(),
    saveRecipeFn: vi.fn(),
}));

vi.mock('../api/recipes-quota-api', () => ({
    fetchRecipeQuotaStatusFn: vi.fn(),
    toggleLiveScheduleFn: vi.fn(),
}));

vi.mock('../api/recipes-studio-api', () => ({
    fetchLivePortfolioAndRunsFn: vi.fn(),
    fetchRecipeAlertsFn: vi.fn(),
    markAlertReadFn: vi.fn(),
    previewStrategyPromptFn: vi.fn(),
    submitWaitlistPledgeFn: vi.fn(),
}));

beforeEach(() => {
    vi.clearAllMocks();
});

describe('RecipeStudioPage', () => {
    it('offers exactly one LLM call with no add or remove stage controls', () => {
        render(<RecipeStudioPage />);

        expect(screen.getByText('LLM Call')).toBeInTheDocument();
        expect(screen.queryByText(/LLM Call #\d/)).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: '+ Add LLM Stage' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Remove Stage' })).not.toBeInTheDocument();
        expect(
            screen.queryByRole('button', { name: '2-Stage Research -> Trade Decision' }),
        ).not.toBeInTheDocument();
    });

    it('saves, enqueues, and navigates to the live backtest route when Backtest is clicked', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({ id: 'rec-42' } as never);
        vi.mocked(enqueueRecipeJobFn).mockResolvedValue({
            id: 'job-777',
            status: 'pending',
        } as never);

        render(<RecipeStudioPage />);

        const backtestBtn = screen.getByRole('button', { name: /Backtest \(Random 2W\)/i });
        fireEvent.click(backtestBtn);

        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/backtest/$jobId',
                params: { jobId: 'job-777' },
            });
        });
    });

    it('renders persisted Live Paper Portfolio & Run Traces for a saved recipe', () => {
        render(
            <RecipeStudioPage
                initialStrategy={{
                    id: 'rec-live-1',
                    name: 'Live Test',
                    cadence: '3h',
                    version: '2.0-push',
                    stages: [
                        {
                            id: 's1',
                            title: 'Stage 1',
                            blocks: [{ id: 'b1', type: 'prompt', text: 'Trade semis' }],
                            selected_tools: ['get_stock_quote'],
                        },
                    ],
                }}
                initialLiveState={{
                    portfolio: {
                        cash: 7500,
                        total_equity: 10125,
                        open_positions: [
                            {
                                ticker: 'NVDA',
                                shares: 12.5,
                                entry_price: 200,
                                entry_time: '2026-11-14 09:30 ET',
                                cost_basis: 2500,
                                current_price: 210,
                                market_value: 2623.69,
                                unrealized_pnl_net: 123.69,
                                unrealized_return_pct: 4.95,
                            },
                        ],
                        trades: [],
                    },
                    recentLiveRuns: [
                        {
                            id: 'live-job-1',
                            mode: 'live_turn',
                            status: 'completed',
                            progress_pct: 100,
                            error_message: null,
                            created_at: '2026-11-15T15:30:00Z',
                            result_json: {
                                mode: 'live_turn',
                                as_of_utc: '2026-11-15T15:30:00Z',
                                slot_label: '2026-11-15 10:30 ET',
                                final_output: '[{"action": "BUY", "ticker": "NVDA"}]',
                                signals: [{ action: 'BUY', ticker: 'NVDA' }],
                                stages: [
                                    {
                                        stage_id: 's1',
                                        title: 'Stage 1',
                                        prompt: 'Live Hydrated Prompt',
                                        output: '[{"action": "BUY", "ticker": "NVDA"}]',
                                        tool_calls: ['get_stock_quote({"ticker":"NVDA"})'],
                                        trace: {
                                            forced_final_synthesis: false,
                                            rounds: [
                                                {
                                                    round: 1,
                                                    reasoning: 'NVDA momentum confirmed.',
                                                    assistant_text: '',
                                                    tool_calls: [
                                                        {
                                                            name: 'get_stock_quote',
                                                            args: { ticker: 'NVDA' },
                                                            result: 'Price: $210.00',
                                                        },
                                                    ],
                                                },
                                            ],
                                        },
                                    },
                                ],
                            },
                        },
                    ],
                }}
            />,
        );

        expect(screen.getByText(/Live Paper Portfolio/i)).toBeInTheDocument();
        expect(screen.getByText('$7,500.00')).toBeInTheDocument();
        expect(screen.getByText('NVDA')).toBeInTheDocument();
        expect(screen.getByText('Live Hydrated Prompt')).toBeInTheDocument();
        expect(screen.getByText('NVDA momentum confirmed.')).toBeInTheDocument();
        expect(screen.getByText('Price: $210.00')).toBeInTheDocument();
    });

    it('updates displayed portfolio from fresh live_turn result immediately even when refresh fails', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({ id: 'rec-live-1' } as never);
        vi.mocked(enqueueRecipeJobFn).mockResolvedValue({
            id: 'live-job-2',
            status: 'completed',
            result_json: {
                mode: 'live_turn',
                as_of_utc: '2026-11-15T18:00:00Z',
                slot_label: '2026-11-15 13:00 ET',
                final_output: '[{"action": "BUY", "ticker": "AVGO"}]',
                signals: [{ action: 'BUY', ticker: 'AVGO' }],
                signal_prices: { AVGO: 180 },
                updated_portfolio: {
                    paper_cash: 6400,
                    paper_positions: [
                        {
                            ticker: 'AVGO',
                            shares: 20,
                            entry_price: 180,
                            entry_time: '2026-11-15 13:00 ET',
                            cost_basis: 3600,
                            current_price: 180,
                            market_value: 3600,
                            unrealized_pnl_net: -1.8,
                            unrealized_return_pct: -0.05,
                        },
                    ],
                    paper_trades: [],
                    paper_equity_curve: [],
                },
                stages: [
                    {
                        stage_id: 's1',
                        title: 'Stage 1',
                        prompt: 'Fresh Prompt',
                        output: '[{"action": "BUY", "ticker": "AVGO"}]',
                        tool_calls: [],
                    },
                ],
            },
        } as never);
        vi.mocked(fetchLivePortfolioAndRunsFn).mockRejectedValue(new Error('Replica lag'));

        render(
            <RecipeStudioPage
                initialStrategy={{
                    id: 'rec-live-1',
                    name: 'Live Test',
                    cadence: '3h',
                    version: '2.0-push',
                    stages: [
                        {
                            id: 's1',
                            title: 'Stage 1',
                            blocks: [{ id: 'b1', type: 'prompt', text: 'Trade semis' }],
                            selected_tools: ['get_stock_quote'],
                        },
                    ],
                }}
                initialLiveState={{
                    portfolio: {
                        cash: 10000,
                        total_equity: 10000,
                        open_positions: [],
                        trades: [],
                    },
                    recentLiveRuns: [],
                }}
            />,
        );

        expect(screen.getAllByText('$10,000.00').length).toBeGreaterThanOrEqual(1);
        fireEvent.click(screen.getByRole('button', { name: /Run Live/i }));

        await waitFor(() => {
            expect(screen.getAllByText('$6,400.00').length).toBeGreaterThanOrEqual(1);
            expect(screen.getByText('AVGO')).toBeInTheDocument();
        });
    });

    it('renders quota status strip and toggles Scheduled Live 3x/day ET', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({
            id: 'rec-sched-1',
            name: 'Live Scheduler Test',
            cadence: '3h',
        } as never);
        vi.mocked(toggleLiveScheduleFn).mockResolvedValue({
            id: 'rec-sched-1',
            is_live: true,
        });
        vi.mocked(fetchRecipeQuotaStatusFn).mockResolvedValue({
            tier: 'beta_starter',
            activeBacktests: 0,
            maxConcurrentBacktests: 1,
            backtestsLast24h: 0,
            dailyBacktestLimit: 2,
            liveTurnsLast24h: 0,
            dailyLiveTurnLimit: 3,
            activeLiveRecipes: 1,
            maxLiveRecipes: 1,
            globalPendingBacktests: 1,
            globalQueueCap: 20,
        });

        render(
            <RecipeStudioPage
                initialQuota={{
                    tier: 'beta_starter',
                    activeBacktests: 0,
                    maxConcurrentBacktests: 1,
                    backtestsLast24h: 0,
                    dailyBacktestLimit: 2,
                    liveTurnsLast24h: 0,
                    dailyLiveTurnLimit: 3,
                    activeLiveRecipes: 0,
                    maxLiveRecipes: 1,
                    globalPendingBacktests: 1,
                    globalQueueCap: 20,
                }}
            />,
        );

        expect(screen.getByText(/Backtests: 2\/2 left today/i)).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /Schedule Live \(3x\/d\)/i }));

        await waitFor(() => {
            expect(toggleLiveScheduleFn).toHaveBeenCalledWith({
                data: { recipeId: 'rec-sched-1', isLive: true },
            });
            expect(
                screen.getByRole('button', { name: /Scheduled Live: ON \(3x\/d\)/i }),
            ).toBeInTheDocument();
        });
    });

    it('surfaces quota errors above the quota strip with danger tokens, logs warning, and offers Waitlist CTA', async () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.mocked(saveRecipeFn).mockResolvedValue({ id: 'rec-quota-1' } as never);
        vi.mocked(enqueueRecipeJobFn).mockRejectedValue(
            new Error(
                'Daily backtest limit reached (2/2 in 24h). Come back tomorrow or request higher capacity via Waitlist.',
            ),
        );

        render(
            <RecipeStudioPage
                initialQuota={{
                    tier: 'beta_starter',
                    activeBacktests: 0,
                    maxConcurrentBacktests: 1,
                    backtestsLast24h: 2,
                    dailyBacktestLimit: 2,
                    liveTurnsLast24h: 0,
                    dailyLiveTurnLimit: 3,
                    activeLiveRecipes: 0,
                    maxLiveRecipes: 1,
                    globalPendingBacktests: 0,
                    globalQueueCap: 20,
                }}
            />,
        );

        const backtestBtn = screen.getByRole('button', { name: /Backtest \(0\/2 Left\)/i });
        fireEvent.click(backtestBtn);

        await waitFor(() => {
            const alert = screen.getByRole('alert');
            expect(alert).toHaveTextContent(/Daily backtest limit reached \(2\/2 in 24h\)/i);
            expect(alert.className).toContain('border-danger');
            expect(alert.className).toContain('text-danger');
            const quotaStrip = screen.getByTestId('recipe-quota-strip');
            expect(
                alert.compareDocumentPosition(quotaStrip) & Node.DOCUMENT_POSITION_FOLLOWING,
            ).toBeTruthy();
        });

        expect(warnSpy).toHaveBeenCalled();
        expect(errorSpy).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole('button', { name: /Request Capacity/i }));
        expect(screen.getByText(/Early Supporter Pledge/i)).toBeInTheDocument();
        warnSpy.mockRestore();
        errorSpy.mockRestore();
    });

    it('preserves fallback backtest link across quota retry and never attaches live_turn jobId', async () => {
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        vi.mocked(saveRecipeFn).mockResolvedValue({ id: 'rec-nav-1' } as never);
        vi.mocked(enqueueRecipeJobFn).mockResolvedValueOnce({
            id: 'job-nav-999',
            status: 'pending',
        } as never);
        mockNavigate.mockRejectedValueOnce(new Error('Navigation aborted'));

        render(<RecipeStudioPage />);
        fireEvent.click(screen.getByRole('button', { name: /Backtest \(Random 2W\)/i }));

        await waitFor(() => {
            const alert = screen.getByRole('alert');
            expect(alert).toHaveTextContent('Navigation aborted');
            const link = screen.getByRole('link', { name: /Open Backtest Run/i });
            expect(link).toHaveAttribute('href', '/recipes/backtest/job-nav-999');
        });
        expect(errorSpy).toHaveBeenCalled();

        // Retry hits concurrent backtest quota limit: fallback link must remain visible
        vi.mocked(enqueueRecipeJobFn).mockRejectedValueOnce(
            new Error('Concurrent backtest limit reached (1/1 active).'),
        );
        fireEvent.click(screen.getByRole('button', { name: /Backtest \(Random 2W\)/i }));

        await waitFor(() => {
            const alert = screen.getByRole('alert');
            expect(alert).toHaveTextContent('Concurrent backtest limit reached');
            expect(screen.getByRole('link', { name: /Open Backtest Run/i })).toHaveAttribute(
                'href',
                '/recipes/backtest/job-nav-999',
            );
        });

        // A live_turn failure after enqueue must never attach a backtest link
        const pollSpy = vi
            .spyOn(liveStudioHelpers, 'pollJobResults')
            .mockRejectedValueOnce(new Error('Live poll crashed'));
        vi.mocked(enqueueRecipeJobFn).mockResolvedValueOnce({
            id: 'live-err-1',
            status: 'pending',
        } as never);
        fireEvent.click(screen.getByRole('button', { name: /Run Live/i }));

        await waitFor(() => {
            const alert = screen.getByRole('alert');
            expect(alert).toHaveTextContent('Live poll crashed');
            expect(
                screen.queryByRole('link', { name: /Open Backtest Run/i }),
            ).not.toBeInTheDocument();
        });

        pollSpy.mockRestore();
        errorSpy.mockRestore();
        warnSpy.mockRestore();
    });

    it('surfaces Schedule Live errors in a single top alert without keeping stale execution errors', async () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.mocked(saveRecipeFn).mockResolvedValue({
            id: 'rec-sched-err',
            name: 'Schedule Error Recipe',
            cadence: '3h',
        } as never);
        vi.mocked(enqueueRecipeJobFn).mockRejectedValueOnce(new Error('Prior backtest error'));
        vi.mocked(toggleLiveScheduleFn).mockRejectedValueOnce(
            new Error('Scheduled live limit reached (1/1). Pause your existing live recipe first.'),
        );

        render(<RecipeStudioPage />);

        fireEvent.click(screen.getByRole('button', { name: /Backtest \(Random 2W\)/i }));
        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent('Prior backtest error');
        });

        fireEvent.click(screen.getByRole('button', { name: /Schedule Live \(3x\/d\)/i }));
        await waitFor(() => {
            const alerts = screen.getAllByRole('alert');
            expect(alerts).toHaveLength(1);
            expect(alerts[0]).toHaveTextContent(/Scheduled live limit reached \(1\/1\)/i);
            expect(screen.getByRole('button', { name: /Request Capacity/i })).toBeInTheDocument();
        });

        expect(warnSpy).toHaveBeenCalled();
        warnSpy.mockRestore();
        errorSpy.mockRestore();
    });
});
