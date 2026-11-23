import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
}));

vi.mock('../api/recipe-jobs-api', () => ({
    fetchLatestRecipeRunFn: vi.fn().mockResolvedValue(null),
}));

vi.mock('../api/recipes-studio-api', () => ({
    previewStrategyPromptFn: vi.fn(),
    submitWaitlistPledgeFn: vi.fn(),
}));

import { fetchLatestRecipeRunFn } from '../api/recipe-jobs-api';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';

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

        // Step 3 is active in the stepper.
        expect(
            screen.getByTestId('builder-stepper').querySelector('[data-step-number="3"]'),
        ).toHaveAttribute('data-step-state', 'active');

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

    it('marks an unsaved compiled bot as dirty so Save Recipe is enabled immediately', () => {
        const unsaved = { ...strategy, id: undefined };
        renderWithQuery(<CompiledBotWorkspace initialStrategy={unsaved} />);

        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeEnabled();
        expect(screen.getByTestId('builder-status')).toHaveTextContent(/draft not saved yet/i);
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
});
