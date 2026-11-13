import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RecipeStudioPage } from './RecipeStudioPage';

vi.mock('../api/recipes-api', () => ({
    enqueueRecipeJobFn: vi.fn(),
    fetchRecipeAlertsFn: vi.fn(),
    getRecipeJobStatusFn: vi.fn(),
    markAlertReadFn: vi.fn(),
    previewStrategyPromptFn: vi.fn(),
    saveRecipeFn: vi.fn(),
    submitWaitlistPledgeFn: vi.fn(),
}));

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
});
