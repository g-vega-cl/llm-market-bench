import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { RecipeOverviewData } from '../types';
import { liveOverviewData } from './overview-test-fixture';
import { RecipeOverviewPage } from './RecipeOverviewPage';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    useNavigate: () => mockNavigate,
    Link: ({
        children,
        to,
        params,
        className,
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
            <a href={href} className={className} {...rest}>
                {children}
            </a>
        );
    },
}));

vi.mock('../api/recipes-api', () => ({
    enqueueRecipeJobFn: vi.fn(),
}));

vi.mock('../api/recipes-quota-api', () => ({
    fetchRecipeQuotaStatusFn: vi.fn(),
    toggleLiveScheduleFn: vi.fn(),
    switchLiveScheduleFn: vi.fn(),
}));

vi.mock('../api/recipes-studio-api', () => ({
    submitWaitlistPledgeFn: vi.fn(),
}));

vi.mock('../api/fork-recipe', () => ({
    forkRecipeFn: vi.fn(),
}));

import { forkRecipeFn } from '../api/fork-recipe';

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

describe('RecipeOverviewPage (hub)', () => {
    it('renders one card with the summary strip and a single link into the detail page', () => {
        const { container } = render(
            <RecipeOverviewPage data={liveOverviewData} initialAtmosphere="dusk" />,
        );

        const stage = container.querySelector('section[data-slot="scene-stage"]');
        expect(stage).toBeInTheDocument();
        expect(stage).toHaveAttribute('data-atmosphere', 'dusk');
        expect(stage).toHaveAttribute('data-backdrop-mode', 'page');
        const world = container.querySelector('[data-slot="scene-backdrop"]');
        expect(world).toHaveClass('fixed');
        expect(screen.getByTestId('cedar-ridge-backdrop')).toHaveAttribute('data-fauna', 'walking');

        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('AI Capex Radar');
        expect(screen.getByRole('link', { name: 'Overview' })).toHaveAttribute(
            'aria-current',
            'page',
        );
        expect(screen.getByRole('link', { name: 'Live Runs' })).toHaveAttribute(
            'href',
            '/recipes/live/rec-live-1',
        );

        const strip = screen.getByTestId('bot-summary-strip');
        expect(strip).toHaveTextContent('Total Equity');
        expect(strip).toHaveTextContent('$10,500.00');
        expect(strip).toHaveTextContent('+5.00%');
        expect(strip).toHaveTextContent('100.0%');
        expect(strip).toHaveTextContent('1 / 4');

        expect(
            screen.getByRole('link', { name: /Performance, behaviors & positions/i }),
        ).toHaveAttribute('href', '/recipes/rec-live-1/performance');

        // The hub serves one purpose: the panels live on the detail page.
        expect(screen.queryByTestId('bot-performance-block')).not.toBeInTheDocument();
        expect(screen.queryByTestId('bot-behaviors-block')).not.toBeInTheDocument();
        expect(screen.queryByTestId('bot-positions-dna-block')).not.toBeInTheDocument();
    });

    it('stands the meadow still when the bot is not live', () => {
        const pausedData: RecipeOverviewData = { ...liveOverviewData, isLive: false };
        render(<RecipeOverviewPage data={pausedData} />);

        expect(screen.getByTestId('cedar-ridge-backdrop')).toHaveAttribute('data-fauna', 'standby');
    });

    it('renders read-only public mode with Fork to My Bots and hides Blueprint tab for non-owners', async () => {
        vi.mocked(forkRecipeFn).mockResolvedValue({
            id: 'fork-99',
            name: 'Copy of AI Capex Radar',
        });

        render(
            <RecipeOverviewPage data={{ ...liveOverviewData, isOwner: false, isPublic: true }} />,
        );

        expect(screen.getByText('PUBLIC BOT')).toBeInTheDocument();
        expect(screen.queryByRole('link', { name: 'Blueprint' })).not.toBeInTheDocument();
        const forkBtn = screen.getByRole('button', { name: 'Fork to My Bots' });
        fireEvent.click(forkBtn);

        await waitFor(() => {
            expect(forkRecipeFn).toHaveBeenCalledWith({ data: { recipeId: 'rec-live-1' } });
            expect(mockNavigate).toHaveBeenCalledWith({
                to: '/recipes/$recipeId',
                params: { recipeId: 'fork-99' },
            });
        });
    });
});
