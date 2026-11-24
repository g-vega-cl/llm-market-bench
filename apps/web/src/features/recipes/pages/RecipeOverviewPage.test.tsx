import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import type { RecipeOverviewData } from '../types';
import { RecipeOverviewPage } from './RecipeOverviewPage';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    useNavigate: () => mockNavigate,
    Link: ({
        children,
        to,
        params,
        className,
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
            <a href={href} className={className} {...rest}>
                {children}
            </a>
        );
    },
}));

vi.mock('../api/recipes-api', () => ({
    enqueueRecipeJobFn: vi.fn(),
}));

vi.mock('../api/recipes-quota-api', () => ({
    fetchRecipeQuotaStatusFn: vi.fn(),
    toggleLiveScheduleFn: vi.fn(),
    switchLiveScheduleFn: vi.fn(),
}));

vi.mock('../api/recipes-studio-api', () => ({
    submitWaitlistPledgeFn: vi.fn(),
}));

vi.mock('../api/fork-recipe', () => ({
    forkRecipeFn: vi.fn(),
}));

import { forkRecipeFn } from '../api/fork-recipe';

function render(ui: React.ReactElement) {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return rtlRender(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

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

beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockResolvedValue(undefined);
});

const liveOverviewData: RecipeOverviewData = {
    recipeId: 'rec-live-1',
    strategy: { ...STARTER_RECIPES[0], id: 'rec-live-1', name: 'AI Capex Radar' },
    isOwner: true,
    isPublic: false,
    isTemplate: false,
    isLive: true,
    turboExpiresAt: null,
    turboUsedToday: false,
    portfolio: {
        cash: 7500,
        total_equity: 10500,
        open_positions: [
            {
                ticker: 'NVDA',
                shares: 10,
                entry_price: 250,
                entry_time: '2026-11-14 09:30 ET',
                current_price: 300,
                market_value: 3000,
                cost_basis: 2500,
                unrealized_pnl_net: 500,
                unrealized_return_pct: 20,
            },
        ],
        trades: [
            {
                ticker: 'AVGO',
                action: 'BUY',
                entry_time: '2026-11-12 09:30 ET',
                entry_price: 180,
                exit_time: '2026-11-13 15:30 ET',
                exit_price: 190,
                pnl_midpoint: 100,
                pnl_net: 96,
                return_pct_midpoint: 5.5,
                return_pct_net: 5.2,
                exit_reason: 'TARGET_HIT',
                catalyst_headline: 'Custom ASIC demand surge',
                confidence: 86,
            },
        ],
        equity_curve: [
            { time: '2026-11-14 09:30 ET', equity: 10000 },
            { time: '2026-11-18 15:30 ET', equity: 10500 },
        ],
    },
    recentLiveRuns: [
        {
            id: 'live-run-1',
            recipe_id: 'rec-live-1',
            mode: 'live_turn',
            status: 'completed',
            progress_pct: 100,
            result_json: {
                mode: 'live_turn',
                as_of_utc: '2026-11-18T15:30:00Z',
                stages: [
                    {
                        stage_id: 's1',
                        prompt: 'Evaluate NVDA',
                        output: 'Maintaining NVDA long on data center strength.',
                        tool_calls: ['get_ticker_news'],
                    },
                ],
                final_output: 'Maintaining NVDA long on data center strength.',
                signals: [{ action: 'BUY', ticker: 'NVDA' }],
            },
            error_message: null,
            created_at: '2026-11-18T15:30:00Z',
        },
    ],
    recentBacktests: [
        {
            id: 'bt-job-1',
            recipe_id: 'rec-live-1',
            mode: 'backtest',
            status: 'completed',
            progress_pct: 100,
            result_json: {
                mode: 'backtest',
                window_dates: ['2026-11-01', '2026-11-14'],
                total_return_pct_midpoint: 7.2,
                total_return_pct_net: 6.8,
                total_trades: 3,
                win_rate_pct: 66.7,
                max_drawdown_pct: 1.8,
                equity_curve: [],
                trades: [],
            },
            error_message: null,
            created_at: '2026-11-10T10:00:00Z',
        },
    ],
};

describe('RecipeOverviewPage', () => {
    it('renders living SceneStage header, 3 structured blocks, benchmark chart, behaviors, positions, and links', async () => {
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
                return {
                    QQQ: [
                        { date: '2026-11-14', price: 400 },
                        { date: '2026-11-18', price: 416 },
                    ],
                };
            },
        );

        const { container } = render(
            <RecipeOverviewPage
                data={liveOverviewData}
                initialAtmosphere="dusk"
                benchmarkFetchFn={benchmarkFetchFn}
            />,
        );

        const stage = container.querySelector('section[data-slot="scene-stage"]');
        expect(stage).toBeInTheDocument();
        expect(stage).toHaveAttribute('data-atmosphere', 'dusk');
        expect(screen.getByTestId('garden-backdrop')).toBeInTheDocument();

        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('AI Capex Radar');
        expect(screen.getByRole('link', { name: 'Overview' })).toHaveAttribute(
            'aria-current',
            'page',
        );
        expect(screen.getByRole('link', { name: 'Live Runs' })).toHaveAttribute(
            'href',
            '/recipes/live/rec-live-1',
        );
        expect(screen.getByRole('link', { name: 'Blueprint' })).toHaveAttribute(
            'href',
            '/recipes/rec-live-1/edit',
        );

        expect(screen.getByTestId('bot-performance-block')).toHaveTextContent('LIVE PAPER');
        expect(screen.getByTestId('bot-performance-block')).toHaveTextContent('$10,500.00');
        expect(screen.getByTestId('bot-behaviors-block')).toHaveTextContent(
            'Maintaining NVDA long on data center strength.',
        );
        expect(screen.getByTestId('bot-positions-dna-block')).toHaveTextContent('BUY AVGO');
        expect(screen.getByRole('link', { name: /Edit Blueprint/i })).toHaveAttribute(
            'href',
            '/recipes/rec-live-1/edit',
        );
        expect(screen.getByRole('link', { name: /2026-11-01 → 2026-11-14/i })).toHaveAttribute(
            'href',
            '/recipes/backtest/bt-job-1',
        );

        await waitFor(() => {
            expect(benchmarkFetchFn).toHaveBeenCalledWith(['SPY'], '2026-11-14', '2026-11-18');
            expect(screen.getByText(/\+3\.00% outperformance/i)).toBeInTheDocument();
        });

        fireEvent.change(screen.getByLabelText(/Benchmark/i), { target: { value: 'QQQ' } });
        await waitFor(() => {
            expect(benchmarkFetchFn).toHaveBeenCalledWith(['QQQ'], '2026-11-14', '2026-11-18');
        });
    });

    it('falls back to latest backtest preview when no live turns exist yet', () => {
        const backtestOnlyData: RecipeOverviewData = {
            ...liveOverviewData,
            isLive: false,
            portfolio: {
                cash: 10000,
                total_equity: 10000,
                open_positions: [],
                trades: [],
                equity_curve: [],
            },
            recentLiveRuns: [],
            recentBacktests: [
                {
                    ...liveOverviewData.recentBacktests[0],
                    result_json: {
                        mode: 'backtest',
                        window_dates: ['2026-11-01', '2026-11-14'],
                        starting_capital: 10000,
                        ending_capital_net: 10680,
                        total_equity: 10680,
                        cash: 10680,
                        total_return_pct_midpoint: 7.2,
                        total_return_pct_net: 6.8,
                        total_trades: 3,
                        winning_trades: 2,
                        win_rate_pct: 66.7,
                        max_drawdown_pct: 1.8,
                        equity_curve: [
                            { time: '2026-11-01', equity: 10000 },
                            { time: '2026-11-01', equity: 10680 },
                        ],
                        trades: [],
                    },
                },
            ],
        };

        render(<RecipeOverviewPage data={backtestOnlyData} benchmarkFetchFn={vi.fn()} />);

        expect(screen.getByTestId('bot-performance-block')).toHaveTextContent('LATEST BACKTEST');
        expect(screen.getByText(/Showing latest 2-week backtest preview/i)).toBeInTheDocument();
        expect(
            screen.getByText(/Benchmark comparison begins once 2\+ trading days/i),
        ).toBeInTheDocument();
    });

    it('renders read-only public mode with Fork to My Bots and hides Blueprint tab for non-owners', async () => {
        vi.mocked(forkRecipeFn).mockResolvedValue({
            id: 'fork-99',
            name: 'Copy of AI Capex Radar',
        });

        render(
            <RecipeOverviewPage
                data={{
                    ...liveOverviewData,
                    isOwner: false,
                    isPublic: true,
                }}
                benchmarkFetchFn={vi.fn()}
            />,
        );

        expect(screen.getByText('PUBLIC BOT')).toBeInTheDocument();
        expect(screen.queryByRole('link', { name: 'Blueprint' })).not.toBeInTheDocument();
        const forkBtn = screen.getByRole('button', { name: 'Fork to My Bots' });
        fireEvent.click(forkBtn);

        await waitFor(() => {
            expect(forkRecipeFn).toHaveBeenCalledWith({ data: { recipeId: 'rec-live-1' } });
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/$recipeId',
                params: { recipeId: 'fork-99' },
            });
        });
    });
});
