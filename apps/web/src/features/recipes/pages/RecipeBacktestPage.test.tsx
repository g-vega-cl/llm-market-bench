import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { BacktestResultData, RecipeRunDetail } from '../types';
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

vi.mock('../api/recipes-quota-api', () => ({
    cancelRecipeJobFn: vi.fn(),
}));

import { enqueueRecipeJobFn, fetchRecipeRunDetailFn } from '../api/recipes-api';
import { cancelRecipeJobFn } from '../api/recipes-quota-api';

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
    recipeCadence: '3h',
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
        expect(screen.getByText('SLOT 3 / 5')).toBeInTheDocument();
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

        // Edit Bot link preserves recipeId and points to /build
        const editLink = screen.getByRole('link', { name: /Edit Bot/i });
        expect(editLink).toHaveAttribute('href', '/build?recipeId=rec-456');
    });

    it('renders Current Portfolio & Open Positions panel with cash, mark price, and unrealized P&L', () => {
        const withOpen: RecipeRunDetail = {
            ...sampleProcessingDetail,
            job: {
                ...sampleProcessingDetail.job,
                result_json: {
                    ...(sampleProcessingDetail.job.result_json as BacktestResultData),
                    cash: 7500,
                    total_equity: 10050,
                    open_positions: [
                        {
                            ticker: 'MSFT',
                            shares: 5.5,
                            entry_price: 420.0,
                            entry_time: '2026-08-04 09:30 ET',
                            cost_basis: 2310.0,
                            current_price: 430.0,
                            market_value: 2363.82,
                            unrealized_pnl_net: 53.82,
                            unrealized_return_pct: 2.33,
                        },
                    ],
                },
            },
        };
        vi.mocked(fetchRecipeRunDetailFn).mockResolvedValue(withOpen);

        renderWithQuery(<RecipeBacktestPage jobId="job-123" initialData={withOpen} />);

        expect(screen.getByText(/Current Portfolio & Open Positions/i)).toBeInTheDocument();
        expect(screen.getByText('$7,500.00')).toBeInTheDocument();
        expect(screen.getAllByText('MSFT').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('+$53.82').length).toBeGreaterThanOrEqual(1);
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

    it('renders queue position badge, Cancel Run control, and read-only showcase mode cleanly', async () => {
        const queuedDetail: RecipeRunDetail = {
            recipeName: 'Queued Showcase',
            recipeCadence: '3h',
            queuePosition: 2,
            job: {
                id: 'job-queued',
                recipe_id: 'rec-q',
                mode: 'backtest',
                status: 'pending',
                progress_pct: 0,
                result_json: null,
                error_message: null,
            },
        };
        vi.mocked(fetchRecipeRunDetailFn).mockResolvedValue(queuedDetail);
        vi.mocked(cancelRecipeJobFn).mockResolvedValue({ id: 'job-queued', status: 'cancelled' });

        const { unmount } = renderWithQuery(
            <RecipeBacktestPage jobId="job-queued" initialData={queuedDetail} />,
        );
        expect(screen.getByText('QUEUED #2')).toBeInTheDocument();
        const cancelBtn = screen.getByRole('button', { name: 'Cancel Run' });
        fireEvent.click(cancelBtn);

        await waitFor(() => {
            expect(cancelRecipeJobFn).toHaveBeenCalledWith({ data: { jobId: 'job-queued' } });
        });
        unmount();

        renderWithQuery(
            <RecipeBacktestPage
                jobId="job-demo"
                initialData={sampleProcessingDetail}
                readOnlyShowcase
            />,
        );
        expect(screen.getByText(/Sign In Free to Build & Run/i)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Cancel Run' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Re-run/i })).not.toBeInTheDocument();
        expect(screen.getByText('How To Read This Backtest')).toBeInTheDocument();
    });

    it('keeps Cancel Run stably mounted while background polling fetch is in flight', () => {
        vi.mocked(fetchRecipeRunDetailFn).mockImplementation(() => new Promise(() => {}));
        renderWithQuery(
            <RecipeBacktestPage jobId="job-123" initialData={sampleProcessingDetail} />,
        );
        expect(screen.getByRole('button', { name: 'Cancel Run' })).toBeInTheDocument();
    });

    it('places Telemetry, Portfolio, and Trades above Session Trace and links them bidirectionally', () => {
        vi.mocked(fetchRecipeRunDetailFn).mockResolvedValue(sampleProcessingDetail);
        const { container } = renderWithQuery(
            <RecipeBacktestPage jobId="job-123" initialData={sampleProcessingDetail} />,
        );

        const timelineEl = container.querySelector('#simulation-timeline');
        const traceEl = container.querySelector('#session-trace');
        const telemetryHeading = screen.getByText(/Developing Telemetry/i);
        const portfolioHeading = screen.getByText(/Current Portfolio & Open Positions/i);
        const tradesHeading = screen.getByText(/Executed Trades \(1\)/i);

        expect(timelineEl).toBeInTheDocument();
        expect(traceEl).toBeInTheDocument();
        if (!timelineEl || !traceEl) throw new Error('Expected timeline and trace sections');

        // DOM order: Timeline -> Telemetry -> Portfolio -> Trades -> Session Trace
        expect(
            timelineEl.compareDocumentPosition(telemetryHeading) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();
        expect(
            telemetryHeading.compareDocumentPosition(portfolioHeading) &
                Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();
        expect(
            portfolioHeading.compareDocumentPosition(tradesHeading) &
                Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();
        expect(
            tradesHeading.compareDocumentPosition(traceEl) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();

        // Bidirectional anchor links
        const jumpToTrace = screen.getByRole('link', { name: /Jump to Trace/i });
        expect(jumpToTrace).toHaveAttribute('href', '#session-trace');
        const backToTimeline = screen.getByRole('link', { name: /Timeline/i });
        expect(backToTimeline).toHaveAttribute('href', '#simulation-timeline');

        // Default is S2 (2026-08-04, HOLD today). Stepping Prev switches to S1 (2026-08-03, NVDA).
        expect(screen.getByText('HOLD today')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /Prev/i }));
        expect(
            screen.getByText('get_technical_indicators({"ticker": "NVDA"})'),
        ).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));
        expect(screen.getByText('HOLD today')).toBeInTheDocument();
    });
});
