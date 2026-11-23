import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { STARTER_RECIPES } from '../starter-templates';
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
    mockNavigate.mockResolvedValue(undefined);
});

describe('RecipeStudioPage > draft and explicit save', () => {
    it('keeps graph edits made while a save is in flight', async () => {
        let resolveSave: (value: never) => void = () => {};
        vi.mocked(saveRecipeFn).mockReturnValue(
            new Promise((resolve) => {
                resolveSave = resolve as (value: never) => void;
            }) as never,
        );

        render(<RecipeStudioPage />);

        fireEvent.change(screen.getByLabelText('Recipe Name'), { target: { value: 'Draft Name' } });
        fireEvent.click(screen.getByRole('button', { name: 'Save Recipe' }));

        // A block edited during the request must not be marked as saved.
        fireEvent.click(screen.getByRole('button', { name: '+ News' }));

        resolveSave({
            id: 'rec-inflight-1',
            name: 'Draft Name',
            cadence: '3h',
            is_live: false,
            trial_count: 0,
            updated_at: '2026-11-16T19:00:00Z',
        } as never);

        await waitFor(() => {
            expect(saveRecipeFn).toHaveBeenCalledTimes(1);
        });
        await waitFor(() => {
            expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeEnabled();
        });
    });

    it('persists the edited draft after a save, then runs backtest with the saved graph', async () => {
        let resolveFirst: (value: never) => void = () => {};
        vi.mocked(saveRecipeFn)
            .mockReturnValueOnce(
                new Promise((resolve) => {
                    resolveFirst = resolve as (value: never) => void;
                }) as never,
            )
            .mockResolvedValue({
                id: 'rec-run-1',
                name: 'Run Draft',
                cadence: '3h',
                is_live: false,
                trial_count: 0,
                updated_at: '2026-11-16T19:00:00Z',
            } as never);
        vi.mocked(enqueueRecipeJobFn).mockResolvedValue({
            id: 'job-run-1',
            status: 'pending',
            result_json: {
                mode: 'backtest',
                window_dates: [],
                days_completed: 0,
                total_days: 30,
                current_day: null,
                starting_capital: 10000,
                ending_capital_midpoint: 10000,
                ending_capital_net: 10000,
                cash: 10000,
                total_equity: 10000,
                open_positions: [],
                total_return_pct_midpoint: 0,
                total_return_pct_net: 0,
                total_trades: 0,
                win_rate_pct: 0,
                equity_curve: [],
                trades: [],
            },
        } as never);

        render(<RecipeStudioPage />);

        fireEvent.change(screen.getByLabelText('Recipe Name'), { target: { value: 'Run Draft' } });
        fireEvent.click(screen.getByRole('button', { name: 'Save Recipe' }));

        // Each action manages its own pending state; backtest is not blocked by an in-flight save.
        expect(screen.getByRole('button', { name: /Backtest \(Random 2W\)/i })).toBeEnabled();

        fireEvent.click(screen.getByRole('button', { name: '+ News' }));

        resolveFirst({
            id: 'rec-run-1',
            name: 'Run Draft',
            cadence: '3h',
            is_live: false,
            trial_count: 0,
            updated_at: '2026-11-16T19:00:00Z',
        } as never);

        await waitFor(() => {
            expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeEnabled();
        });

        fireEvent.click(screen.getByRole('button', { name: /Backtest \(Random 2W\)/i }));

        await waitFor(() => {
            expect(saveRecipeFn).toHaveBeenCalledTimes(2);
        });

        const secondPayload = vi.mocked(saveRecipeFn).mock.calls[1][0] as {
            data: { recipe: { stages: { blocks: unknown[] }[] } };
        };
        const originalBlocks = STARTER_RECIPES[0].stages[0].blocks.length;
        expect(secondPayload.data.recipe.stages[0].blocks).toHaveLength(originalBlocks + 1);
    });

    it('shows a save failure inline and keeps the draft saveable', async () => {
        vi.mocked(saveRecipeFn).mockRejectedValue(
            new Error('Unauthorized: please sign in to save recipes'),
        );

        render(<RecipeStudioPage />);

        fireEvent.change(screen.getByLabelText('Recipe Name'), { target: { value: 'Draft Name' } });
        fireEvent.click(screen.getByRole('button', { name: 'Save Recipe' }));

        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Unauthorized: please sign in to save recipes',
        );
        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeEnabled();
    });

    it('treats a selected template as an unsaved draft', () => {
        render(
            <RecipeStudioPage
                initialStrategy={{
                    id: 'rec-saved-1',
                    name: 'Trump & Chips News Momentum',
                    cadence: '3h',
                    version: '2.0-push',
                    stages: [
                        {
                            id: 's1',
                            blocks: [{ id: 'b1', type: 'prompt', text: 'Trade semis' }],
                            selected_tools: [],
                        },
                    ],
                }}
            />,
        );

        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeDisabled();

        fireEvent.click(screen.getByRole('button', { name: /QNMR/ }));

        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeEnabled();
    });

    it('saves the typed name explicitly without enqueueing a job', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({
            id: 'rec-explicit-1',
            name: 'Semis Rotation',
            cadence: '3h',
            is_live: false,
            trial_count: 0,
            updated_at: '2026-11-16T19:00:00Z',
        } as never);

        render(<RecipeStudioPage />);

        // Nothing persisted yet, so the template itself can be saved explicitly.
        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeEnabled();

        fireEvent.change(screen.getByLabelText('Recipe Name'), {
            target: { value: 'Semis Rotation' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Save Recipe' }));

        await waitFor(() => {
            expect(saveRecipeFn).toHaveBeenCalledWith({
                data: {
                    recipe: expect.objectContaining({ name: 'Semis Rotation' }),
                    // The explicit Save button is the restore path.
                    restore: true,
                },
            });
        });
        expect(enqueueRecipeJobFn).not.toHaveBeenCalled();
        expect(await screen.findByRole('button', { name: 'Saved' })).toBeDisabled();
        expect(screen.getByText('Semis Rotation')).toBeInTheDocument();
    });

    it('sends the typed recipe name and renders the name the server persisted', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({
            id: 'rec-named-1',
            name: 'Small-Cap Rotation',
            cadence: '3h',
            is_live: false,
            trial_count: 0,
            updated_at: '2026-11-16T19:00:00Z',
        } as never);
        vi.mocked(enqueueRecipeJobFn).mockResolvedValue({
            id: 'job-named-1',
            status: 'pending',
        } as never);

        render(<RecipeStudioPage />);

        expect(screen.getByLabelText('Recipe Name')).toHaveValue('Trump & Chips News Momentum');

        fireEvent.change(screen.getByLabelText('Recipe Name'), {
            target: { value: '  Small-Cap Rotation  ' },
        });
        fireEvent.click(screen.getByRole('button', { name: /Backtest \(Random 2W\)/i }));

        await waitFor(() => {
            expect(saveRecipeFn).toHaveBeenCalledWith({
                data: {
                    recipe: expect.objectContaining({ name: '  Small-Cap Rotation  ' }),
                    restore: false,
                },
            });
        });
        await waitFor(() => {
            expect(screen.getByLabelText('Recipe Name')).toHaveValue('Small-Cap Rotation');
        });
        expect(screen.getByText('Small-Cap Rotation')).toBeInTheDocument();
    });

    it('shows the server-normalized name after saving a blank one', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({
            id: 'rec-blank-1',
            name: 'Untitled Strategy',
            cadence: '3h',
            is_live: false,
            trial_count: 0,
            updated_at: '2026-11-16T19:00:00Z',
        } as never);
        vi.mocked(enqueueRecipeJobFn).mockResolvedValue({
            id: 'job-blank-1',
            status: 'pending',
        } as never);

        render(<RecipeStudioPage />);

        fireEvent.change(screen.getByLabelText('Recipe Name'), { target: { value: '   ' } });
        fireEvent.click(screen.getByRole('button', { name: /Backtest \(Random 2W\)/i }));

        await waitFor(() => {
            expect(screen.getByLabelText('Recipe Name')).toHaveValue('Untitled Strategy');
        });
    });
});
