import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { enqueueRecipeJobFn } from '../api/recipes-api';
import type { RecipeOverviewData, RecipeUserQuotaStatus } from '../types';
import { liveOverviewData } from './overview-test-fixture';
import { RecipeOverviewDetailsPage } from './RecipeOverviewDetailsPage';

vi.mock('@tanstack/react-router', () => ({
    useNavigate: () => vi.fn(),
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
});

/**
 * The block's owner actions (Run 2W Backtest, Enable Live) only render in its
 * empty state — with an equity curve the chart takes that slot.
 */
const noCurveData: RecipeOverviewData = {
    ...liveOverviewData,
    isLive: false,
    isOwner: true,
    portfolio: { ...liveOverviewData.portfolio, equity_curve: [] },
    recentLiveRuns: [],
    recentBacktests: [],
};

describe('RecipeOverviewDetailsPage', () => {
    it('renders performance and positions behind a back link, without behaviours', async () => {
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
            <RecipeOverviewDetailsPage
                data={liveOverviewData}
                initialAtmosphere="dusk"
                benchmarkFetchFn={benchmarkFetchFn}
            />,
        );

        // Detail chrome: back link to the Overview tab, and this page's own chip.
        expect(
            screen.getByRole('link', { name: /Back to AI Capex Radar Overview/i }),
        ).toHaveAttribute('href', '/recipes/rec-live-1');
        expect(screen.getByRole('link', { name: 'Performance' })).toHaveAttribute(
            'aria-current',
            'page',
        );
        // The hub owns the visible h1; this page still needs one of its own.
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
            'AI Capex Radar — Performance & positions',
        );
        expect(container.querySelector('section[data-slot="scene-stage"]')).toHaveAttribute(
            'data-backdrop-mode',
            'page',
        );

        expect(screen.getByTestId('bot-performance-block')).toHaveTextContent('LIVE PAPER');
        expect(screen.getByTestId('bot-performance-block')).toHaveTextContent('$10,500.00');
        // Behaviours have their own tab now; this page must not render them twice.
        expect(screen.queryByTestId('bot-behaviors-block')).not.toBeInTheDocument();
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

        render(<RecipeOverviewDetailsPage data={backtestOnlyData} benchmarkFetchFn={vi.fn()} />);

        // A paused bot stands still: the shell's fauna axis reads the schedule.
        expect(screen.getByTestId('cedar-ridge-backdrop')).toHaveAttribute('data-fauna', 'standby');

        expect(screen.getByTestId('bot-performance-block')).toHaveTextContent('LATEST BACKTEST');
        expect(screen.getByText(/Showing latest 2-week backtest preview/i)).toBeInTheDocument();
        expect(
            screen.getByText(/Benchmark comparison begins once 2\+ trading days/i),
        ).toBeInTheDocument();
    });

    it('renders the live-switch confirmation when the owner is already at the live cap', () => {
        const quota: RecipeUserQuotaStatus = {
            tier: 'free',
            activeBacktests: 0,
            maxConcurrentBacktests: 1,
            backtestsLast24h: 0,
            dailyBacktestLimit: 3,
            liveTurnsLast24h: 0,
            dailyLiveTurnLimit: 24,
            activeLiveRecipes: 1,
            maxLiveRecipes: 1,
            globalPendingBacktests: 0,
            globalQueueCap: 100,
        };

        render(
            <RecipeOverviewDetailsPage
                data={noCurveData}
                initialQuota={quota}
                initialUserRecipes={[
                    {
                        id: 'other-bot',
                        name: 'Other Bot',
                        cadence: '3h',
                        is_live: true,
                        trial_count: 0,
                        updated_at: '2026-11-20T00:00:00.000Z',
                    },
                ]}
                benchmarkFetchFn={vi.fn()}
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));

        // Without this surface the button is a silent no-op: the toggle parks in
        // `confirming` and waits for a confirmation nobody renders.
        expect(screen.getByRole('alert')).toHaveTextContent('Other Bot is currently live');
        expect(screen.getByRole('button', { name: /Switch to This/i })).toBeInTheDocument();
    });

    it('surfaces a rejected backtest as an alert instead of swallowing it', async () => {
        vi.mocked(enqueueRecipeJobFn).mockRejectedValue(
            new Error('Quota exceeded: 3/3 backtests today'),
        );

        render(<RecipeOverviewDetailsPage data={noCurveData} benchmarkFetchFn={vi.fn()} />);

        fireEvent.click(screen.getByRole('button', { name: /Run 2W Backtest/i }));

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent(/Quota exceeded/);
        });
    });
});
