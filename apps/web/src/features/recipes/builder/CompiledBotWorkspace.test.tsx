import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
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

vi.mock('../api/recipes-studio-api', () => ({
    previewStrategyPromptFn: vi.fn(),
    submitWaitlistPledgeFn: vi.fn(),
}));

import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';

beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockResolvedValue(undefined);
});

describe('CompiledBotWorkspace', () => {
    const strategy = STARTER_RECIPES[0];

    it('keeps block editor and raw prompt collapsed by default and offers one primary Backtest CTA', () => {
        render(<CompiledBotWorkspace initialStrategy={strategy} />);

        expect(
            screen.getByRole('button', { name: /▶ Backtest \(Random 2W\)/i }),
        ).toBeInTheDocument();
        expect(screen.queryByText('LLM Call')).not.toBeInTheDocument();
        expect(screen.queryByText('Prompt Visualizer')).not.toBeInTheDocument();

        // Expand blocks & tools drawer
        fireEvent.click(screen.getByRole('button', { name: /Edit blocks & tools/i }));
        expect(screen.getByText('LLM Call')).toBeInTheDocument();
        expect(screen.queryByText('Prompt Visualizer')).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Select All' })).not.toBeInTheDocument();

        // Expand nested raw prompt toggle
        fireEvent.click(screen.getByRole('button', { name: /View raw prompt/i }));
        expect(screen.getByText('Prompt Visualizer')).toBeInTheDocument();
    });

    it('marks an unsaved compiled bot as dirty so Save Recipe is enabled immediately', () => {
        const unsaved = { ...strategy, id: undefined };
        render(<CompiledBotWorkspace initialStrategy={unsaved} />);

        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeEnabled();
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

        render(<CompiledBotWorkspace initialStrategy={strategy} />);

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
});
