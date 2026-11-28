import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import {
    activateRecipeTurboFn,
    fetchRecipeQuotaStatusFn,
    switchLiveScheduleFn,
    toggleLiveScheduleFn,
} from '../api/recipes-quota-api';
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
    activateRecipeTurboFn: vi.fn(),
    fetchRecipeQuotaStatusFn: vi.fn(),
    toggleLiveScheduleFn: vi.fn(),
    switchLiveScheduleFn: vi.fn(),
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
    mockNavigate.mockResolvedValue(undefined);
});

describe('RecipeStudioPage > basic rendering', () => {
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

    it('does not render LiveRunsBlock (moved to dedicated page)', () => {
        render(<RecipeStudioPage />);

        expect(screen.queryByText(/Live Paper Portfolio/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Live Run Traces/i)).not.toBeInTheDocument();
    });

    it('renders the Enable Live button instead of Run Live', () => {
        render(<RecipeStudioPage />);

        expect(screen.getByRole('button', { name: 'Enable Live (30m)' })).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Run Live/i })).not.toBeInTheDocument();
    });
});

describe('RecipeStudioPage > runs, quota, and scheduling', () => {
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

    it('renders quota status strip and toggles Live 30m ET', async () => {
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

        expect(screen.getByTestId('token-balance').textContent).toContain('Tokens:');
        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));

        await waitFor(() => {
            expect(toggleLiveScheduleFn).toHaveBeenCalledWith({
                data: { recipeId: 'rec-sched-1', isLive: true },
            });
            expect(screen.getByRole('button', { name: /Live: ON \(30m\)/i })).toBeInTheDocument();
        });
    });

    it('shows confirmation trough when enabling live while another recipe is live', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({
            id: 'rec-new-1',
            name: 'New Recipe',
            cadence: '3h',
        } as never);
        vi.mocked(switchLiveScheduleFn).mockResolvedValueOnce({
            pausedId: 'rec-old-1',
            enabledId: 'rec-new-1',
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
            globalPendingBacktests: 0,
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
                    activeLiveRecipes: 1,
                    maxLiveRecipes: 1,
                    globalPendingBacktests: 0,
                    globalQueueCap: 20,
                }}
                initialUserRecipes={[
                    {
                        id: 'rec-old-1',
                        name: 'Old Live Recipe',
                        cadence: '3h',
                        is_live: true,
                        is_public: true,
                        trial_count: 1,
                        updated_at: '',
                    },
                ]}
            />,
        );

        // Click Enable Live — should show confirmation trough
        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));

        await waitFor(() => {
            const alert = screen.getByRole('alert');
            expect(alert).toHaveTextContent(/Old Live Recipe/i);
            expect(alert).toHaveTextContent(/Enable live for/i);
            expect(alert).toHaveTextContent(/instead\?/i);
            expect(screen.getByRole('button', { name: 'Switch to This' })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Keep current' })).toBeInTheDocument();
        });

        // Click Switch to This — should switch atomically and navigate
        fireEvent.click(screen.getByRole('button', { name: 'Switch to This' }));

        await waitFor(() => {
            expect(switchLiveScheduleFn).toHaveBeenCalledTimes(1);
            expect(switchLiveScheduleFn).toHaveBeenCalledWith({
                data: { pauseRecipeId: 'rec-old-1', enableRecipeId: 'rec-new-1' },
            });
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/live/$recipeId/runs',
                params: { recipeId: 'rec-new-1' },
            });
        });
    });

    it('cancels live switch when Keep is clicked', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({
            id: 'rec-new-1',
            name: 'New Recipe',
            cadence: '3h',
        } as never);
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
            globalPendingBacktests: 0,
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
                    activeLiveRecipes: 1,
                    maxLiveRecipes: 1,
                    globalPendingBacktests: 0,
                    globalQueueCap: 20,
                }}
                initialUserRecipes={[
                    {
                        id: 'rec-old-1',
                        name: 'Old Live Recipe',
                        cadence: '3h',
                        is_live: true,
                        is_public: true,
                        trial_count: 1,
                        updated_at: '',
                    },
                ]}
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));

        await waitFor(() => {
            expect(screen.getByRole('alert')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByRole('button', { name: 'Keep current' }));

        await waitFor(() => {
            expect(screen.queryByRole('alert')).not.toBeInTheDocument();
            expect(toggleLiveScheduleFn).not.toHaveBeenCalled();
        });
    });

    it('surfaces quota errors above the quota strip with danger tokens, logs warning, and offers Waitlist CTA', async () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.mocked(saveRecipeFn).mockResolvedValue({ id: 'rec-quota-1' } as never);
        vi.mocked(enqueueRecipeJobFn).mockRejectedValue(
            new Error('You are out of tokens. Refills Monday 09:30 ET.'),
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
                    tokenBalance: 0,
                    tokenGrant: 15,
                    tokenRefillLabel: 'refills Monday 09:30 ET',
                }}
            />,
        );

        const backtestBtn = screen.getByRole('button', { name: /Backtest \(0 tokens left\)/i });
        fireEvent.click(backtestBtn);

        await waitFor(() => {
            const alert = screen.getByRole('alert');
            expect(alert).toHaveTextContent(/out of tokens/i);
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

    it('preserves fallback backtest link across quota retry', async () => {
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

        errorSpy.mockRestore();
        warnSpy.mockRestore();
    });

    it('surfaces Schedule Live errors in a single top alert', async () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        vi.mocked(saveRecipeFn).mockResolvedValue({
            id: 'rec-sched-err',
            name: 'Schedule Error Recipe',
            cadence: '3h',
        } as never);
        vi.mocked(toggleLiveScheduleFn).mockRejectedValueOnce(
            new Error('Scheduled live limit reached (1/1). Pause your existing live recipe first.'),
        );

        render(<RecipeStudioPage />);

        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));
        await waitFor(() => {
            const alerts = screen.getAllByRole('alert');
            expect(alerts).toHaveLength(1);
            expect(alerts[0]).toHaveTextContent(/Scheduled live limit reached \(1\/1\)/i);
            expect(screen.getByRole('button', { name: /Request Capacity/i })).toBeInTheDocument();
        });

        expect(warnSpy).toHaveBeenCalled();
        warnSpy.mockRestore();
    });

    it('activates Turbo from Studio action bar when viewing a live bot during market hours', async () => {
        vi.useFakeTimers({ shouldAdvanceTime: true });
        vi.setSystemTime(new Date('2026-11-18T11:00:00-05:00'));

        vi.mocked(activateRecipeTurboFn).mockResolvedValue({
            recipeId: 'rec-live-turbo',
            turboExpiresAt: '2026-11-18T12:00:00-05:00',
            enqueuedJobId: 'job-turbo-2',
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
            maxLiveRecipes: 3,
            globalPendingBacktests: 0,
            globalQueueCap: 20,
            turboUsedToday: true,
        });

        render(
            <RecipeStudioPage
                initialStrategy={{
                    id: 'rec-live-turbo',
                    version: '2.0-push',
                    name: 'Live Turbo Bot',
                    description: 'Test',
                    cadence: '3h',
                    stages: [
                        {
                            id: 's1',
                            selected_tools: [],
                            blocks: [{ id: 'b1', type: 'prompt', text: 'Analyze NVDA' }],
                        },
                    ],
                }}
                initialUserRecipes={[
                    {
                        id: 'rec-live-turbo',
                        name: 'Live Turbo Bot',
                        cadence: '3h',
                        is_live: true,
                        is_public: true,
                        trial_count: 1,
                        updated_at: '',
                    },
                ]}
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /Turbo \(5m x 1h\)/i }));

        await waitFor(() => {
            expect(activateRecipeTurboFn).toHaveBeenCalledWith({
                data: { recipeId: 'rec-live-turbo' },
            });
            expect(screen.getByRole('button', { name: /Turbo: 60m left \(5m\)/i })).toBeDisabled();
        });
        vi.useRealTimers();
    });
});
