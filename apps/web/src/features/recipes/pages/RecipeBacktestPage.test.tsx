import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { RecipeRunDetail } from '../types';
import { RecipeBacktestPage } from './RecipeBacktestPage';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        search,
    }: {
        children: React.ReactNode;
        to: string;
        search?: Record<string, string>;
    }) => {
        const qs = search?.recipeId ? `?recipeId=${search.recipeId}` : '';
        return <a href={`${to}${qs}`}>{children}</a>;
    },
    useNavigate: () => mockNavigate,
}));

vi.mock('../api/recipes-api', () => ({
    enqueueRecipeJobFn: vi.fn(),
    fetchRecipeRunDetailFn: vi.fn(),
}));

import { enqueueRecipeJobFn, fetchRecipeRunDetailFn } from '../api/recipes-api';

function renderWithQuery(ui: React.ReactElement) {
    const client = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
    return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const sampleProcessingDetail: RecipeRunDetail = {
    recipeName: 'Chip Tariff Momentum',
    recipeCadence: '1d',
    job: {
        id: 'job-123',
        recipe_id: 'rec-456',
        mode: 'backtest',
        status: 'processing',
        progress_pct: 36,
        provider: 'auto-strata',
        model: 'strata',
        error_message: null,
        result_json: {
            mode: 'backtest',
            window_dates: ['2026-08-03', '2026-08-04', '2026-08-05', '2026-08-06', '2026-08-07'],
            days_completed: 2,
            total_days: 5,
            current_day: '2026-08-05',
            starting_capital: 10000,
            ending_capital_midpoint: 10100,
            ending_capital_net: 10099,
            total_return_pct_midpoint: 1.0,
            total_return_pct_net: 0.99,
            total_trades: 1,
            winning_trades: 1,
            losing_trades: 0,
            win_rate_pct: 100,
            profit_factor: 99,
            max_drawdown_pct: 0,
            llm_calls_made: 2,
            equity_curve: [
                { time: '2026-08-03', equity: 10099 },
                { time: '2026-08-04', equity: 10099 },
            ],
            trades: [
                {
                    ticker: 'NVDA',
                    action: 'BUY',
                    entry_time: '2026-08-03',
                    entry_price: 100,
                    exit_time: '2026-08-04',
                    exit_price: 110,
                    pnl_midpoint: 100,
                    pnl_net: 99,
                    return_pct_midpoint: 10.0,
                    return_pct_net: 9.9,
                    exit_reason: 'NEXT_DAY_CLOSE',
                    confidence: 100,
                },
            ],
            skipped_trades: [],
            day_steps: [
                {
                    day: '2026-08-03',
                    day_index: 0,
                    status: 'completed',
                    signals: [{ action: 'BUY', ticker: 'NVDA' }],
                    tool_calls: ['get_technical_indicators({"ticker": "NVDA"})'],
                    output_excerpt: '[{"action": "BUY", "ticker": "NVDA"}]',
                    day_pnl_net: 99,
                    trades_executed: 1,
                    trades_skipped: 0,
                },
                {
                    day: '2026-08-04',
                    day_index: 1,
                    status: 'completed',
                    signals: [],
                    tool_calls: [],
                    output_excerpt: 'HOLD today',
                    day_pnl_net: 0,
                    trades_executed: 0,
                    trades_skipped: 0,
                },
            ],
        },
    },
};

beforeEach(() => {
    vi.clearAllMocks();
});

describe('RecipeBacktestPage', () => {
    it('renders live streaming progress, day tiles, and allows inspecting a completed day in-flow', () => {
        vi.mocked(fetchRecipeRunDetailFn).mockResolvedValue(sampleProcessingDetail);

        renderWithQuery(
            <RecipeBacktestPage jobId="job-123" initialData={sampleProcessingDetail} />,
        );

        expect(screen.getByText('Chip Tariff Momentum')).toBeInTheDocument();
        expect(screen.getByText('DAY 3 / 5')).toBeInTheDocument();
        expect(screen.getByText('36%')).toBeInTheDocument();
        expect(screen.getAllByText('$10,099.00').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('+0.99%')).toBeInTheDocument();

        // Toggle P&L model to Midpoint (Zero-Cost) and back
        fireEvent.click(screen.getByRole('button', { name: 'Midpoint (Zero-Cost)' }));
        expect(screen.getByText('$10,100.00')).toBeInTheDocument();
        expect(screen.getByText('+1.00%')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'Spread & Slippage Net' }));

        // Day 1 tile and Day 3 active tile and Day 4 pending tile
        expect(screen.getByRole('button', { name: /2026-08-03/ })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /2026-08-05/ })).toHaveTextContent('RUNNING');
        expect(screen.getByRole('button', { name: /2026-08-06/ })).toHaveTextContent('QUEUED');

        // Default inspector shows latest completed day (2026-08-04), clicking Day 1 updates inspector
        expect(screen.getByText('HOLD today')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /2026-08-03/ }));
        expect(
            screen.getByText('get_technical_indicators({"ticker": "NVDA"})'),
        ).toBeInTheDocument();
        expect(screen.getByText('[{"action": "BUY", "ticker": "NVDA"}]')).toBeInTheDocument();

        // Executed trade is already visible while backtest is still running
        expect(screen.getByText('Executed Trades (1)')).toBeInTheDocument();
        expect(screen.getAllByText('BUY NVDA').length).toBeGreaterThanOrEqual(1);

        // Edit in Studio link preserves recipeId
        const editLink = screen.getByRole('link', { name: /Edit in Studio/i });
        expect(editLink).toHaveAttribute('href', '/recipes?recipeId=rec-456');
    });

    it('renders queued state cleanly before window dates are selected', () => {
        const queuedDetail: RecipeRunDetail = {
            recipeName: 'Queued Strategy',
            recipeCadence: '1d',
            job: {
                id: 'job-queued',
                recipe_id: 'rec-1',
                mode: 'backtest',
                status: 'pending',
                progress_pct: 0,
                result_json: null,
                error_message: null,
            },
        };
        vi.mocked(fetchRecipeRunDetailFn).mockResolvedValue(queuedDetail);

        renderWithQuery(<RecipeBacktestPage jobId="job-queued" initialData={queuedDetail} />);

        expect(screen.getByText('QUEUED')).toBeInTheDocument();
        expect(screen.getByText(/Waiting for recipe worker/i)).toBeInTheDocument();
    });

    it('renders failed error banner and allows re-running when completed or failed', async () => {
        const failedDetail: RecipeRunDetail = {
            recipeName: 'Broken Strategy',
            recipeCadence: '1d',
            job: {
                id: 'job-err',
                recipe_id: 'rec-999',
                mode: 'backtest',
                status: 'failed',
                progress_pct: 15,
                result_json: null,
                error_message: 'LLM proxy timeout after failover',
            },
        };
        vi.mocked(fetchRecipeRunDetailFn).mockResolvedValue(failedDetail);
        vi.mocked(enqueueRecipeJobFn).mockResolvedValue({
            id: 'job-rerun-1',
            status: 'pending',
        } as never);

        renderWithQuery(<RecipeBacktestPage jobId="job-err" initialData={failedDetail} />);

        expect(screen.getByText('FAILED')).toBeInTheDocument();
        expect(screen.getByText('LLM proxy timeout after failover')).toBeInTheDocument();

        const rerunBtn = screen.getByRole('button', { name: /Re-run Backtest/i });
        fireEvent.click(rerunBtn);

        await waitFor(() => {
            expect(enqueueRecipeJobFn).toHaveBeenCalledWith({
                data: { recipeId: 'rec-999', mode: 'backtest' },
            });
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/backtest/$jobId',
                params: { jobId: 'job-rerun-1' },
            });
        });
    });

    it('uses flex-wrap and whitespace-nowrap fragments on header meta row for 360px mobile safety', () => {
        vi.mocked(fetchRecipeRunDetailFn).mockResolvedValue(sampleProcessingDetail);
        renderWithQuery(
            <RecipeBacktestPage jobId="job-123" initialData={sampleProcessingDetail} />,
        );

        const metaRow = screen.getByTestId('backtest-meta-row');
        expect(metaRow).toHaveClass('flex-wrap');
        const fragments = metaRow.querySelectorAll('span.whitespace-nowrap');
        expect(fragments.length).toBeGreaterThanOrEqual(2);
    });

    it('renders loading boundary while pending without initialData and guards live_turn jobs', () => {
        vi.mocked(fetchRecipeRunDetailFn).mockImplementation(() => new Promise(() => {}));
        renderWithQuery(<RecipeBacktestPage jobId="job-loading" initialData={null} />);
        expect(screen.getByText('Loading Backtest Run...')).toBeInTheDocument();

        const liveDetail: RecipeRunDetail = {
            recipeName: 'Live Only',
            recipeCadence: '1d',
            job: {
                id: 'job-live',
                recipe_id: 'rec-live',
                mode: 'live_turn',
                status: 'completed',
                progress_pct: 100,
                result_json: null,
                error_message: null,
            },
        };
        vi.mocked(fetchRecipeRunDetailFn).mockResolvedValue(liveDetail);
        renderWithQuery(<RecipeBacktestPage jobId="job-live" initialData={liveDetail} />);
        expect(screen.getByText('Incompatible Job Mode')).toBeInTheDocument();
    });
});
