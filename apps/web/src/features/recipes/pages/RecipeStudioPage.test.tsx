import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { fetchRecipeQuotaStatusFn, toggleLiveScheduleFn } from '../api/recipes-quota-api';
import { fetchLivePortfolioAndRunsFn } from '../api/recipes-studio-api';
import { RecipeStudioPage } from './RecipeStudioPage';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
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
});
