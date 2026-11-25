import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import type { RecipeJobRecord } from '../types';
import { CompiledBotWorkspace } from './CompiledBotWorkspace';

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
            ? Object.entries(params).reduce((acc, [k, v]) => acc.replace(`$${k}`, v), to)
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
    saveRecipeFn: vi.fn(),
}));

vi.mock('../api/recipes-quota-api', () => ({
    fetchRecipeQuotaStatusFn: vi.fn(),
    toggleLiveScheduleFn: vi.fn(),
    switchLiveScheduleFn: vi.fn(),
}));

vi.mock('../api/recipe-jobs-api', () => ({
    fetchLatestRecipeRunFn: vi.fn().mockResolvedValue(null),
}));

vi.mock('../api/recipes-studio-api', () => ({
    previewStrategyPromptFn: vi.fn(),
    submitWaitlistPledgeFn: vi.fn(),
    fetchLivePortfolioAndRunsFn: vi.fn().mockResolvedValue(null),
}));

import { fetchLatestRecipeRunFn } from '../api/recipe-jobs-api';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { switchLiveScheduleFn, toggleLiveScheduleFn } from '../api/recipes-quota-api';

function renderWithQuery(ui: React.ReactElement) {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const runningJob: RecipeJobRecord = {
    id: 'job-1',
    recipe_id: 'saved-123',
    mode: 'backtest',
    status: 'processing',
    progress_pct: 41,
    result_json: null,
    error_message: null,
};

beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockResolvedValue(undefined);
    vi.mocked(fetchLatestRecipeRunFn).mockResolvedValue(null);
});

describe('CompiledBotWorkspace', () => {
    const strategy = STARTER_RECIPES[0];

    it('renders hero summary with a single status badge, Step 3 stepper, and defaults lower tab to Blocks & Tools', () => {
        const { container } = renderWithQuery(
            <CompiledBotWorkspace initialStrategy={{ ...strategy, id: undefined }} />,
        );

        expect(container.querySelector('section[data-slot="scene-stage"]')).toBeNull();
        expect(screen.queryByTestId('garden-backdrop')).toBeNull();

        // Only ONE BOT READY badge is rendered (inside BuilderStatusStrip, never duplicated).
        expect(screen.getAllByText('BOT READY')).toHaveLength(1);

        // Step 3 is active in the stepper, and the stepper sits below the primary CTA card.
        const stepper = screen.getByTestId('builder-stepper');
        expect(stepper.querySelector('[data-step-number="3"]')).toHaveAttribute(
            'data-step-state',
            'active',
        );

        // The compiled state is still the /build page: exactly one sr-only h1 carries the name
        const pageHeadings = screen.getAllByRole('heading', { level: 1 });
        expect(pageHeadings).toHaveLength(1);
        expect(pageHeadings[0]).toHaveClass('sr-only');
        expect(pageHeadings[0]).toHaveTextContent('Build a trading bot from one sentence');

        const heroCard = screen.getByTestId('compiled-bot-hero-card');
        expect(heroCard).toHaveClass('voxel-card');
        expect(heroCard).not.toHaveClass('scene-scrim');
        expect(heroCard.querySelectorAll('.voxel-card')).toHaveLength(0);

        const backtestBtn = screen.getByRole('button', { name: /▶ Backtest \(Random 2W\)/i });
        expect(backtestBtn).toBeInTheDocument();
        expect(backtestBtn).toHaveClass('voxel-btn--hero');
        expect(
            backtestBtn.compareDocumentPosition(stepper) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();
        expect(screen.getByTestId('compiled-bot-next-action')).toHaveTextContent(
            /next best step: run a 2-week paper backtest/i,
        );

        // Lower workspace renders Blocks & Tools flat by default inside an accessible tabpanel
        const blocksTab = screen.getByRole('tab', { name: /Blocks & Tools/i });
        const promptTab = screen.getByRole('tab', { name: /Prompt Preview/i });
        expect(blocksTab).toHaveAttribute('aria-selected', 'true');
        expect(blocksTab).toHaveAttribute('aria-controls', 'panel-blocks');
        expect(promptTab).toHaveAttribute('aria-selected', 'false');
        expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'tab-blocks');

        expect(screen.getByText('LLM Call')).toBeInTheDocument();
        expect(screen.queryByText('Prompt Visualizer')).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Select All' })).not.toBeInTheDocument();

        // Keyboard ArrowRight switches to Prompt Preview tabpanel
        fireEvent.keyDown(screen.getByRole('tablist'), { key: 'ArrowRight' });
        expect(promptTab).toHaveAttribute('aria-selected', 'true');
        expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'tab-prompt');
        expect(screen.getByText('Prompt Visualizer')).toBeInTheDocument();
        expect(screen.queryByText('LLM Call')).not.toBeInTheDocument();
    });

    it('marks an unsaved compiled bot as dirty and navigates to /recipes/$recipeId after Save Recipe', async () => {
        const unsaved = { ...strategy, id: undefined };
        vi.mocked(saveRecipeFn).mockResolvedValue({
            ...strategy,
            id: 'new-saved-99',
        } as never);

        renderWithQuery(<CompiledBotWorkspace initialStrategy={unsaved} />);

        const saveBtn = screen.getByRole('button', { name: 'Save Recipe' });
        expect(saveBtn).toBeEnabled();
        expect(screen.getByTestId('builder-status')).toHaveTextContent(/draft not saved yet/i);

        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(saveRecipeFn).toHaveBeenCalledTimes(1);
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/$recipeId',
                params: { recipeId: 'new-saved-99' },
            });
        });
    });

    it('shows a running backtest for this recipe so background work is visible', async () => {
        vi.mocked(fetchLatestRecipeRunFn).mockResolvedValue(runningJob);

        renderWithQuery(
            <CompiledBotWorkspace initialStrategy={{ ...strategy, id: 'saved-123' }} />,
        );

        await waitFor(() => expect(screen.getByTestId('builder-status')).toHaveTextContent(/41%/));
        const strip = screen.getByTestId('builder-status');
        expect(strip).toHaveTextContent(/BACKTEST RUNNING/i);
        expect(fetchLatestRecipeRunFn).toHaveBeenCalledWith({ data: { recipeId: 'saved-123' } });
    });

    it('keeps the unsaved-draft warning visible even when an older run exists', async () => {
        vi.mocked(fetchLatestRecipeRunFn).mockResolvedValue({
            ...runningJob,
            status: 'completed',
            progress_pct: 100,
        });

        renderWithQuery(
            <CompiledBotWorkspace initialStrategy={{ ...strategy, id: 'saved-123' }} />,
        );

        await waitFor(() =>
            expect(screen.getByTestId('builder-status')).toHaveTextContent(/finished/i),
        );

        // Rename the bot: the graph is now dirty while the settled run is still shown.
        fireEvent.change(screen.getByPlaceholderText('Name this strategy'), {
            target: { value: 'Chip Momentum v2' },
        });

        const strip = screen.getByTestId('builder-status');
        expect(strip).toHaveTextContent(/draft not saved yet/i);
        expect(strip).toHaveTextContent(/finished/i);
        // The strip carries the run link itself: no hunting through My Bots.
        expect(screen.getByRole('link', { name: /open run/i })).toHaveAttribute(
            'href',
            '/recipes/backtest/job-1',
        );
    });

    it('auto-saves and navigates to backtest results when clicking Backtest', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({
            ...strategy,
            id: 'saved-123',
        } as never);
        vi.mocked(enqueueRecipeJobFn).mockResolvedValue({
            id: 'job-999',
            status: 'pending',
        } as never);

        renderWithQuery(<CompiledBotWorkspace initialStrategy={strategy} />);

        fireEvent.click(screen.getByRole('button', { name: /▶ Backtest \(Random 2W\)/i }));

        await waitFor(() => {
            expect(saveRecipeFn).toHaveBeenCalledTimes(1);
            expect(enqueueRecipeJobFn).toHaveBeenCalledWith({
                data: { recipeId: 'saved-123', mode: 'backtest' },
            });
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/backtest/$jobId',
                params: { jobId: 'job-999' },
            });
        });
    });

    it('blocks saving or running when the prompt block is cleared to empty', () => {
        renderWithQuery(<CompiledBotWorkspace initialStrategy={strategy} />);

        fireEvent.change(screen.getByLabelText('Prompt text'), { target: { value: '   ' } });

        expect(screen.getByTestId('builder-status')).toHaveTextContent(/PROMPT NEEDED/i);
        expect(screen.getByRole('button', { name: /▶ Backtest \(Random 2W\)/i })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeDisabled();
    });

    it('renders a live-run warning banner and elevates Enable Live when warning is passed while keeping Backtest enabled', () => {
        renderWithQuery(
            <CompiledBotWorkspace
                initialStrategy={strategy}
                warning="Super PAC data is unavailable offline; run this bot live."
            />,
        );

        expect(screen.getByTestId('builder-status')).toHaveTextContent(/LIVE RECOMMENDED/i);
        const warningBox = screen.getByTestId('compiled-bot-live-warning');
        expect(warningBox).toHaveTextContent(/Super PAC data is unavailable offline/i);
        expect(warningBox).toHaveTextContent(/Enable Live \(30m\)/i);

        expect(screen.getByTestId('compiled-bot-next-action')).toHaveTextContent(
            /recommended next step: run the bot live/i,
        );
        const liveBtn = screen.getByRole('button', { name: /Enable Live \(30m\)/i });
        const backtestBtn = screen.getByRole('button', { name: /▶ Backtest \(Random 2W\)/i });
        expect(liveBtn).toHaveClass('voxel-btn--hero');
        expect(backtestBtn).not.toHaveClass('voxel-btn--hero');
        expect(backtestBtn).toBeEnabled();
    });

    it('shows the live-run warning automatically when a liveOnly tool is toggled on in ToolPicker', () => {
        renderWithQuery(<CompiledBotWorkspace initialStrategy={strategy} />);

        expect(screen.queryByTestId('compiled-bot-live-warning')).not.toBeInTheDocument();

        fireEvent.click(screen.getByLabelText('Congress Trades'));

        const warningBox = screen.getByTestId('compiled-bot-live-warning');
        expect(warningBox).toHaveTextContent(/get_congress_trades/i);
        expect(warningBox).toHaveTextContent(/Enable Live \(30m\)/i);
        expect(screen.getByTestId('builder-status')).toHaveTextContent(/LIVE RECOMMENDED/i);
        expect(screen.getByRole('button', { name: /▶ Backtest \(Random 2W\)/i })).toBeEnabled();
    });

    it('suppresses the Enable Live warning banner when the bot is already scheduled live or prompt is empty', () => {
        const liveStrategy = {
            ...strategy,
            id: 'live-123',
            stages: [
                {
                    ...strategy.stages[0],
                    selected_tools: ['get_congress_trades'],
                },
            ] as typeof strategy.stages,
        };
        const { unmount } = renderWithQuery(
            <CompiledBotWorkspace
                initialStrategy={liveStrategy}
                initialUserRecipes={[
                    {
                        id: 'live-123',
                        name: liveStrategy.name,
                        cadence: '3h',
                        is_live: true,
                        is_public: true,
                        trial_count: 1,
                        updated_at: '2026-11-23T00:00:00Z',
                    },
                ]}
            />,
        );

        expect(screen.getByTestId('bot-live-status')).toHaveTextContent(/LIVE ON \(30m\)/i);
        expect(screen.queryByTestId('compiled-bot-live-warning')).not.toBeInTheDocument();
        unmount();

        renderWithQuery(
            <CompiledBotWorkspace
                initialStrategy={strategy}
                warning="Super PAC data is unavailable offline."
            />,
        );
        expect(screen.getByTestId('compiled-bot-live-warning')).toBeInTheDocument();
        fireEvent.change(screen.getByLabelText('Prompt text'), { target: { value: '  ' } });
        expect(screen.getByTestId('builder-status')).toHaveTextContent(/PROMPT NEEDED/i);
        expect(screen.queryByTestId('compiled-bot-live-warning')).not.toBeInTheDocument();
    });

    it('saves, enables live, shows Enabling Live... while in flight, and navigates to live status', async () => {
        let resolveToggle!: (value: { id: string; is_live: boolean }) => void;
        vi.mocked(saveRecipeFn).mockResolvedValue({
            ...strategy,
            id: 'saved-live-1',
        } as never);
        vi.mocked(toggleLiveScheduleFn).mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolveToggle = resolve;
                }) as never,
        );

        renderWithQuery(<CompiledBotWorkspace initialStrategy={{ ...strategy, id: undefined }} />);

        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));

        expect(await screen.findByRole('button', { name: /Enabling Live\.\.\./i })).toBeDisabled();

        resolveToggle({ id: 'saved-live-1', is_live: true });

        await waitFor(() => {
            expect(saveRecipeFn).toHaveBeenCalledTimes(1);
            expect(toggleLiveScheduleFn).toHaveBeenCalledWith({
                data: { recipeId: 'saved-live-1', isLive: true },
            });
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/live/$recipeId/runs',
                params: { recipeId: 'saved-live-1' },
            });
        });
    });

    it('surfaces a single role="alert" in StudioAlertSlot when save or envelope fails on Enable Live', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue(undefined as never);

        renderWithQuery(<CompiledBotWorkspace initialStrategy={{ ...strategy, id: undefined }} />);

        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));

        await waitFor(() => {
            const alerts = screen.getAllByRole('alert');
            expect(alerts).toHaveLength(1);
            expect(alerts[0]).toHaveTextContent(/Saving strategy did not come back/i);
        });
        expect(toggleLiveScheduleFn).not.toHaveBeenCalled();
    });

    it('keeps LiveSwitchConfirmation visible with switching state and switches atomically via switchLiveScheduleFn', async () => {
        let resolveSwitch!: (value: {
            pausedId: string;
            enabledId: string;
            is_live: boolean;
        }) => void;
        vi.mocked(saveRecipeFn).mockResolvedValue({
            ...strategy,
            id: 'new-live-2',
        } as never);
        vi.mocked(switchLiveScheduleFn).mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveSwitch = resolve;
                }) as never,
        );

        renderWithQuery(
            <CompiledBotWorkspace
                initialStrategy={{ ...strategy, id: undefined }}
                initialQuota={{
                    tier: 'beta_starter',
                    activeBacktests: 0,
                    maxConcurrentBacktests: 1,
                    backtestsLast24h: 0,
                    dailyBacktestLimit: 2,
                    liveTurnsLast24h: 0,
                    dailyLiveTurnLimit: 100,
                    activeLiveRecipes: 1,
                    maxLiveRecipes: 1,
                    globalPendingBacktests: 0,
                    globalQueueCap: 20,
                    lastTurboEtDate: null,
                    turboUsedToday: false,
                }}
                initialUserRecipes={[
                    {
                        id: 'old-live-1',
                        name: 'Existing Live Bot',
                        cadence: '3h',
                        is_live: true,
                        is_public: true,
                        trial_count: 1,
                        updated_at: '2026-11-23T00:00:00Z',
                    },
                ]}
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));
        const switchBtn = await screen.findByRole('button', { name: 'Switch to This' });
        fireEvent.click(switchBtn);

        expect(screen.getByRole('button', { name: 'Switch to This' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Switch to This' })).toHaveAttribute(
            'aria-busy',
            'true',
        );

        await waitFor(() => expect(switchLiveScheduleFn).toHaveBeenCalledTimes(1));
        expect(switchLiveScheduleFn).toHaveBeenCalledWith({
            data: { pauseRecipeId: 'old-live-1', enableRecipeId: 'new-live-2' },
        });
        resolveSwitch({ pausedId: 'old-live-1', enabledId: 'new-live-2', is_live: true });

        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/live/$recipeId/runs',
                params: { recipeId: 'new-live-2' },
            });
        });
    });

    it('does not pause the existing live bot if saving the replacement fails during confirmSwitch', async () => {
        vi.mocked(saveRecipeFn).mockRejectedValue(new Error('Save failed'));

        renderWithQuery(
            <CompiledBotWorkspace
                initialStrategy={{ ...strategy, id: undefined }}
                initialQuota={{
                    tier: 'beta_starter',
                    activeBacktests: 0,
                    maxConcurrentBacktests: 1,
                    backtestsLast24h: 0,
                    dailyBacktestLimit: 2,
                    liveTurnsLast24h: 0,
                    dailyLiveTurnLimit: 100,
                    activeLiveRecipes: 1,
                    maxLiveRecipes: 1,
                    globalPendingBacktests: 0,
                    globalQueueCap: 20,
                    lastTurboEtDate: null,
                    turboUsedToday: false,
                }}
                initialUserRecipes={[
                    {
                        id: 'old-live-1',
                        name: 'Existing Live Bot',
                        cadence: '3h',
                        is_live: true,
                        is_public: true,
                        trial_count: 1,
                        updated_at: '2026-11-23T00:00:00Z',
                    },
                ]}
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /Enable Live \(30m\)/i }));
        fireEvent.click(await screen.findByRole('button', { name: 'Switch to This' }));

        await waitFor(() => {
            const alerts = screen.getAllByRole('alert');
            expect(alerts).toHaveLength(1);
            expect(alerts[0]).toHaveTextContent(/Save failed/i);
        });
        expect(switchLiveScheduleFn).not.toHaveBeenCalled();
        expect(toggleLiveScheduleFn).not.toHaveBeenCalled();
    });

    describe('live status block', () => {
        const liveTurn: RecipeJobRecord = {
            id: 'live-run-1',
            recipe_id: 'live-123',
            mode: 'live_turn',
            status: 'completed',
            progress_pct: 100,
            result_json: null,
            error_message: null,
            created_at: '2026-11-24T19:00:00Z',
            completed_at: '2026-11-24T19:00:51Z',
        };

        const liveRecipe = { ...strategy, id: 'live-123' };
        const liveSummary = {
            id: 'live-123',
            name: strategy.name,
            cadence: '3h' as const,
            is_live: true,
            is_public: true,
            trial_count: 1,
            updated_at: '2026-11-24T19:00:00Z',
        };
        const liveSnapshot = {
            totalEquity: 10412,
            cash: 10412,
            isLive: true,
            isOwner: true,
            turboExpiresAt: null,
            lastRun: liveTurn,
            fetchedAt: '2026-11-24T19:01:00Z',
        };

        it('is the first block of the hero card and carries state, next run, last turn and equity', () => {
            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={liveRecipe}
                    initialUserRecipes={[liveSummary]}
                    initialLive={liveSnapshot}
                />,
            );

            const heroCard = screen.getByTestId('compiled-bot-hero-card');
            const banner = screen.getByTestId('bot-live-status');
            expect(heroCard.firstElementChild).toBe(banner);
            expect(banner).toHaveTextContent(/LIVE ON \(30m\)/i);
            expect(banner).toHaveTextContent(/Next run/i);
            expect(banner).toHaveTextContent(/Last turn .*completed/i);
            expect(banner).toHaveTextContent(/Equity \$10,412\.00/);
            expect(banner).toHaveTextContent(/Cash \$10,412\.00/);
            expect(within(banner).getByRole('link', { name: /open live runs/i })).toHaveAttribute(
                'href',
                '/recipes/live/live-123/runs',
            );
        });

        it('keeps the live state when the snapshot read failed, without inventing a history', () => {
            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={liveRecipe}
                    initialUserRecipes={[liveSummary]}
                    initialLive={null}
                />,
            );

            const banner = screen.getByTestId('bot-live-status');
            expect(banner).toHaveTextContent(/LIVE ON \(30m\)/i);
            expect(banner).toHaveTextContent(/Live history not loaded/i);
            expect(banner).not.toHaveTextContent(/No live turns yet/i);
            expect(banner).not.toHaveTextContent(/Equity/i);
        });

        it('reports PAUSED with no next run and no live link when the bot is not scheduled', () => {
            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={liveRecipe}
                    initialUserRecipes={[{ ...liveSummary, is_live: false }]}
                />,
            );

            const banner = screen.getByTestId('bot-live-status');
            expect(banner).toHaveTextContent(/PAUSED/i);
            expect(banner).toHaveTextContent(/Next run Paused/i);
            expect(within(banner).queryByRole('link')).toBeNull();
        });

        it('reports an unknown schedule instead of claiming PAUSED when neither read resolved', () => {
            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={liveRecipe}
                    initialUserRecipes={[]}
                    initialLive={null}
                />,
            );

            const banner = screen.getByTestId('bot-live-status');
            expect(banner).toHaveTextContent(/SCHEDULE UNKNOWN/i);
            expect(banner).toHaveTextContent(/Next run unknown/i);
            expect(banner).not.toHaveTextContent(/PAUSED/i);
            expect(screen.getByTestId('builder-status')).not.toHaveTextContent(/LIVE RECOMMENDED/i);
        });

        it('does not adopt the live schedule of a bot the viewer does not own', () => {
            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={liveRecipe}
                    initialUserRecipes={[]}
                    initialLive={{ ...liveSnapshot, isLive: false, isOwner: false }}
                />,
            );

            expect(screen.getByTestId('bot-live-status')).toHaveTextContent(/SCHEDULE UNKNOWN/i);
        });

        it('trusts the live snapshot when the bot is outside the My Bots window', () => {
            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={liveRecipe}
                    initialUserRecipes={[]}
                    initialLive={liveSnapshot}
                />,
            );

            const banner = screen.getByTestId('bot-live-status');
            expect(banner).toHaveTextContent(/LIVE ON \(30m\)/i);
            expect(banner).not.toHaveTextContent(/PAUSED/i);
            expect(screen.getByTestId('builder-status')).not.toHaveTextContent(/LIVE RECOMMENDED/i);
        });

        it('does not advise enabling live on a bot that is already live, even when it came from a fallback template', () => {
            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={{ ...liveRecipe, stages: liveRecipe.stages }}
                    initialUserRecipes={[liveSummary]}
                    initialLive={liveSnapshot}
                    fallback
                    warning="Super PAC data is unavailable offline; run this bot live."
                />,
            );

            expect(screen.queryByTestId('compiled-bot-live-warning')).not.toBeInTheDocument();
            expect(screen.getByTestId('bot-live-status')).toHaveTextContent(/LIVE ON \(30m\)/i);
        });

        it('surfaces a failed live turn instead of a green equity line', () => {
            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={liveRecipe}
                    initialUserRecipes={[liveSummary]}
                    initialLive={{
                        ...liveSnapshot,
                        lastRun: {
                            ...liveTurn,
                            status: 'failed' as const,
                            error_message: 'LLM timeout',
                        },
                    }}
                />,
            );

            expect(screen.getByTestId('bot-live-status')).toHaveTextContent(/Last turn .*failed/i);
        });

        it('reports a Turbo window as the next run when the bot is boosted', () => {
            // isTurboActive() gates on the ET regular session, so the clock has to be pinned
            // inside market hours: on the real clock this assertion fails every run after
            // 16:00 ET and in any CI job that happens to land after the close.
            vi.useFakeTimers({ shouldAdvanceTime: true });
            vi.setSystemTime(new Date('2026-11-18T11:00:00-05:00'));
            try {
                const turboExpiresAt = new Date(Date.now() + 3 * 60_000).toISOString();
                renderWithQuery(
                    <CompiledBotWorkspace
                        initialStrategy={liveRecipe}
                        initialUserRecipes={[{ ...liveSummary, turbo_expires_at: turboExpiresAt }]}
                        initialLive={liveSnapshot}
                    />,
                );

                const banner = screen.getByTestId('bot-live-status');
                expect(banner).toHaveTextContent(/Next run within 5m \(Turbo\)/i);
                expect(banner).toHaveTextContent(/3m left|m left/i);
            } finally {
                vi.useRealTimers();
            }
        });

        it('does not render for an unsaved draft, where there is no live state yet', () => {
            renderWithQuery(
                <CompiledBotWorkspace initialStrategy={{ ...strategy, id: undefined }} />,
            );

            expect(screen.queryByTestId('bot-live-status')).toBeNull();
            expect(screen.getByTestId('builder-status')).toHaveTextContent(/BOT READY/i);
        });

        it('keeps the work status line below it, so an unsaved draft stays visible on a live bot', async () => {
            vi.mocked(fetchLatestRecipeRunFn).mockResolvedValue({
                ...runningJob,
                recipe_id: 'live-123',
                status: 'processing',
            });

            renderWithQuery(
                <CompiledBotWorkspace
                    initialStrategy={liveRecipe}
                    initialUserRecipes={[liveSummary]}
                    initialLive={liveSnapshot}
                />,
            );

            fireEvent.change(screen.getByPlaceholderText('Name this strategy'), {
                target: { value: 'Renamed live bot' },
            });

            await waitFor(() =>
                expect(screen.getByTestId('builder-status')).toHaveTextContent(
                    /draft not saved yet/i,
                ),
            );
            expect(screen.getByTestId('bot-live-status')).toHaveTextContent(/LIVE ON \(30m\)/i);
            expect(screen.getByTestId('builder-status')).not.toHaveTextContent(/LIVE ACTIVE/i);
        });
    });
});
