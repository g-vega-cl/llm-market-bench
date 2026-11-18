import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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

    it('does not render LiveRunsBlock (moved to dedicated page)', () => {
        render(<RecipeStudioPage />);

        expect(screen.queryByText(/Live Paper Portfolio/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Live Run Traces/i)).not.toBeInTheDocument();
    });

    it('renders the Enable Live button instead of Run Live', () => {
        render(<RecipeStudioPage />);

        expect(screen.getByRole('button', { name: 'Enable Live (3x/d)' })).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Run Live/i })).not.toBeInTheDocument();
    });
});
