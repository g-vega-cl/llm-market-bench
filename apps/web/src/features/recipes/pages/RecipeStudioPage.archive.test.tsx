import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { archiveRecipeFn } from '../api/archive-recipe';
import { saveRecipeFn } from '../api/recipes-api';
import { STARTER_RECIPES } from '../starter-templates';
import type { RecipeSummaryItem } from '../types';
import { RecipeStudioPage } from './RecipeStudioPage';

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
    useNavigate: () => vi.fn(),
}));

vi.mock('../api/archive-recipe', () => ({
    archiveRecipeFn: vi.fn(),
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

const savedStrategies: RecipeSummaryItem[] = [
    {
        id: 'rec-1',
        name: 'Claude Agent Portfolio Mirror',
        cadence: '3h',
        is_live: false,
        trial_count: 2,
        updated_at: '2026-11-17T12:00:00.000Z',
    },
    {
        id: 'rec-2',
        name: 'Quality Value Screener',
        cadence: '3h',
        is_live: false,
        trial_count: 0,
        updated_at: '2026-11-16T12:00:00.000Z',
    },
];

beforeEach(() => {
    vi.clearAllMocks();
});

describe('RecipeStudioPage > removing a strategy', () => {
    it('hides the removed strategy only after the server confirms it', async () => {
        let confirm: (value: unknown) => void = () => {};
        vi.mocked(archiveRecipeFn).mockReturnValue(
            new Promise((resolve) => {
                confirm = resolve;
            }) as never,
        );

        render(<RecipeStudioPage initialUserRecipes={savedStrategies} />);

        fireEvent.click(
            screen.getByRole('button', {
                name: 'Remove Quality Value Screener from My Strategies',
            }),
        );

        // No optimistic removal: the chip survives until the server confirms.
        expect(screen.getByRole('link', { name: /Quality Value Screener/ })).toBeInTheDocument();
        expect(
            screen.getByRole('button', {
                name: 'Remove Quality Value Screener from My Strategies',
            }),
        ).toHaveAttribute('aria-busy', 'true');

        confirm({ id: 'rec-2', archived_at: '2026-11-17T14:00:00.000Z', cancelled_jobs: 0 });

        await waitFor(() => {
            expect(
                screen.queryByRole('link', { name: /Quality Value Screener/ }),
            ).not.toBeInTheDocument();
        });
        expect(archiveRecipeFn).toHaveBeenCalledWith({ data: { recipeId: 'rec-2' } });
        expect(
            screen.getByRole('link', { name: /Claude Agent Portfolio Mirror/ }),
        ).toBeInTheDocument();
    });

    it('keeps the chip and reports the failure when the hide call fails', async () => {
        vi.mocked(archiveRecipeFn).mockRejectedValue(new Error('Unauthorized'));

        render(<RecipeStudioPage initialUserRecipes={savedStrategies} />);

        fireEvent.click(
            screen.getByRole('button', {
                name: 'Remove Quality Value Screener from My Strategies',
            }),
        );

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent('Unauthorized');
        });
        expect(screen.getByRole('link', { name: /Quality Value Screener/ })).toBeInTheDocument();
    });

    it('closes the editor of the removed strategy so a later run cannot resurrect it', async () => {
        vi.mocked(archiveRecipeFn).mockResolvedValue({
            id: 'rec-2',
            archived_at: '2026-11-17T14:00:00.000Z',
            cancelled_jobs: 0,
        } as never);

        render(
            <RecipeStudioPage
                initialUserRecipes={savedStrategies}
                initialStrategy={{
                    ...STARTER_RECIPES[0],
                    id: 'rec-2',
                    name: 'Quality Value Screener',
                }}
            />,
        );

        expect(screen.getByLabelText('Recipe Name')).toHaveValue('Quality Value Screener');

        fireEvent.click(
            screen.getByRole('button', {
                name: 'Remove Quality Value Screener from My Strategies',
            }),
        );

        await waitFor(() => {
            expect(screen.getByLabelText('Recipe Name')).toHaveValue(STARTER_RECIPES[0].name);
        });
        // The removed row is no longer open, so nothing can re-save it.
        expect(saveRecipeFn).not.toHaveBeenCalled();
    });
});

describe('RecipeStudioPage > templates', () => {
    it('lists all sixteen starter templates in the shared code grid with the selected description', () => {
        render(<RecipeStudioPage />);

        const grid = screen.getByTestId('template-code-grid');
        expect(within(grid).getAllByRole('button')).toHaveLength(16);
        // Each cell is labelled by its type code; the recipe name lives in the in-flow line.
        expect(within(grid).getByRole('button', { name: /QNMR/ })).toBeInTheDocument();
        expect(within(grid).getByRole('button', { name: /LNFR/ })).toBeInTheDocument();
        expect(within(grid).getByRole('button', { name: /LVFP/ })).toBeInTheDocument();

        expect(screen.getByTestId('template-code-grid-description')).toHaveTextContent(
            /News-driven momentum/i,
        );
    });
});
