import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { RecipeEditPage } from './RecipeEditPage';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    useNavigate: () => mockNavigate,
    Link: ({
        children,
        to,
        params,
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
            <a href={href} {...rest}>
                {children}
            </a>
        );
    },
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
}));

vi.mock('../api/fork-recipe', () => ({
    forkRecipeFn: vi.fn(),
}));

import { saveRecipeFn } from '../api/recipes-api';

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
    mockNavigate.mockResolvedValue(undefined);
});

describe('RecipeEditPage', () => {
    const strategy = { ...STARTER_RECIPES[0], id: 'rec-edit-1', name: 'Chip Momentum' };

    it('renders BotStageHeader with Blueprint active, Blocks & Tools editor, and saves edits', async () => {
        vi.mocked(saveRecipeFn).mockResolvedValue({
            ...strategy,
            name: 'Chip Momentum v2',
        } as never);

        render(
            <RecipeEditPage
                recipeId="rec-edit-1"
                initialStrategy={strategy}
                initialIsLive={false}
                initialAtmosphere="daylight"
            />,
        );

        expect(screen.getByRole('link', { name: 'Blueprint' })).toHaveAttribute(
            'aria-current',
            'page',
        );
        expect(screen.getByRole('link', { name: 'Overview' })).toHaveAttribute(
            'href',
            '/recipes/rec-edit-1',
        );

        const saveBtn = screen.getByRole('button', { name: 'Save Recipe' });
        expect(saveBtn).toBeDisabled();

        fireEvent.change(screen.getByPlaceholderText('Name this strategy'), {
            target: { value: 'Chip Momentum v2' },
        });
        expect(saveBtn).toBeEnabled();

        fireEvent.click(saveBtn);
        await waitFor(() => {
            expect(saveRecipeFn).toHaveBeenCalledTimes(1);
        });
    });
});
