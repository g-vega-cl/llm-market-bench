import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
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

vi.mock('../api/recipes-studio-api', () => ({
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
});
