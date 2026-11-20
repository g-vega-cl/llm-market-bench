import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RecipeDeskHomePage } from '~/features/home/pages/RecipeDeskHomePage';
import type { PublicDesk } from '~/features/recipes/api/public-board-api';
import { normalizeLeaderboard, Route } from './index';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-start', () => ({
    createServerFn: () => ({
        handler: (fn: unknown) => fn,
        validator: () => ({ handler: (fn: unknown) => fn }),
    }),
}));

vi.mock('~/features/recipes/api/fork-recipe', () => ({
    forkRecipeFn: vi.fn(),
}));

vi.mock('~/features/recipes/api/public-board-api', () => ({
    fetchPublicDesk: vi.fn(),
}));

vi.mock('@tanstack/react-router', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/react-router')>();
    return {
        ...actual,
        Link: ({ to, children, ...rest }: { to: string; children: React.ReactNode }) => (
            <a href={to} {...rest}>
                {children}
            </a>
        ),
        useRouter: () => ({ navigate: mockNavigate }),
    };
});

const desk: PublicDesk = {
    cards: [
        {
            recipeId: 'r-new',
            name: 'Chip Momentum',
            returnPct: 3.2,
            spyReturnPct: 1.1,
            tradeCount: 4,
            openPositions: 2,
            runsToday: 2,
            lastRunAt: '2026-11-19T15:30:00+00:00',
            lastAction: { action: 'EXIT', ticker: 'NVDA', price: 181.2, reason: 'Thesis broken' },
            resolvedModel: 'tencent/hy4-flash:free',
        },
        {
            recipeId: 'r-old',
            name: 'Value Screener',
            returnPct: -4.5,
            spyReturnPct: 3.1,
            tradeCount: 1,
            openPositions: 0,
            runsToday: 1,
            lastRunAt: '2026-11-18T15:30:00+00:00',
            lastAction: null,
            resolvedModel: null,
        },
    ],
    feed: [
        {
            at: '2026-11-19T15:30:00+00:00',
            recipeId: 'r-new',
            recipeName: 'Chip Momentum',
            action: 'EXIT',
            ticker: 'NVDA',
        },
    ],
    liveCount: 2,
    beatSpyCount: 1,
    medianReturnPct: -0.65,
};

describe('Recipe desk homepage', () => {
    it('renders every card and publishes a losing recipe', () => {
        render(<RecipeDeskHomePage desk={desk} onFork={vi.fn()} />);

        expect(screen.getAllByText('Chip Momentum').length).toBeGreaterThan(0);
        expect(screen.getByText('Value Screener')).toBeInTheDocument();
        expect(screen.getByText('-4.50%')).toBeInTheDocument();
        expect(screen.getByText('+3.20%')).toBeInTheDocument();
    });

    it('shows the live and beat-SPY counts on the desk header', () => {
        render(<RecipeDeskHomePage desk={desk} onFork={vi.fn()} />);

        expect(screen.getByText(/2 live/)).toBeInTheDocument();
        expect(screen.getByText(/1 beating SPY/)).toBeInTheDocument();
    });

    it('shows the portfolio median in the hero, not the desk median', () => {
        render(
            <RecipeDeskHomePage
                desk={desk}
                leaderboard={{
                    rows: [],
                    spy: [],
                    medianReturnPct: -2.55,
                    trackedCount: 30,
                    windowDays: 30,
                    degraded: false,
                    spyUnavailable: false,
                }}
                onFork={vi.fn()}
            />,
        );

        expect(screen.getByText(/-2\.55%/)).toBeInTheDocument();
        expect(screen.queryByText(/-0\.65%/)).not.toBeInTheDocument();
    });

    it('says the board is unavailable when the read degraded', () => {
        render(
            <RecipeDeskHomePage
                desk={desk}
                leaderboard={{
                    rows: [],
                    spy: [],
                    medianReturnPct: null,
                    trackedCount: 0,
                    windowDays: 30,
                    degraded: true,
                    spyUnavailable: false,
                }}
                onFork={vi.fn()}
            />,
        );

        expect(screen.getByText(/board is unavailable right now/i)).toBeInTheDocument();
        expect(screen.queryByText(/fills after the next close/i)).not.toBeInTheDocument();
    });

    it('renders the today feed for executed signals', () => {
        render(<RecipeDeskHomePage desk={desk} onFork={vi.fn()} />);

        expect(screen.getAllByText('NVDA').length).toBeGreaterThan(0);
        expect(screen.getAllByText('EXIT').length).toBeGreaterThan(0);
    });

    it('forks the recipe the visitor clicked', () => {
        const onFork = vi.fn();
        render(<RecipeDeskHomePage desk={desk} onFork={onFork} />);

        fireEvent.click(screen.getAllByRole('button', { name: 'Fork' })[0]);

        expect(onFork).toHaveBeenCalledWith('r-new');
    });

    it('sends the one-line idea to the builder instead of opening a blank editor', () => {
        render(<RecipeDeskHomePage desk={desk} onFork={vi.fn()} />);

        fireEvent.change(screen.getByLabelText('Describe your strategy'), {
            target: { value: 'buy chips on capex news' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Build it' }));

        expect(mockNavigate).toHaveBeenCalledWith({
            to: '/build',
            search: { idea: 'buy chips on capex news' },
        });
    });

    it('falls back to an empty state instead of an empty grid', () => {
        render(
            <RecipeDeskHomePage
                desk={{
                    ...desk,
                    cards: [],
                    feed: [],
                    liveCount: 0,
                    beatSpyCount: 0,
                    medianReturnPct: null,
                }}
                onFork={vi.fn()}
            />,
        );

        expect(screen.getByText('No live recipes yet')).toBeInTheDocument();
    });

    it('surfaces a fork failure in-flow', () => {
        render(<RecipeDeskHomePage desk={desk} onFork={vi.fn()} error="Fork failed: network" />);

        expect(screen.getByRole('alert')).toHaveTextContent('Fork failed: network');
    });
});

describe('public model label', () => {
    it('renders the model without the free-tier suffix', () => {
        render(<RecipeDeskHomePage desk={desk} onFork={vi.fn()} />);

        expect(screen.getByText('run on tencent/hy4-flash')).toBeInTheDocument();
        expect(screen.queryByText(/:free/)).not.toBeInTheDocument();
    });
});

describe('Homepage route', () => {
    it('exports a loader and a component', () => {
        expect(Route.options.loader).toBeTypeOf('function');
        expect(Route.options.component).toBeTypeOf('function');
    });
});

describe('desk payload skew', () => {
    it('renders an empty desk when a cached client receives a partial payload', () => {
        // A stale bundle can hand this route an older/newer loader shape; the
        // route must degrade to the empty state instead of the error boundary.
        render(
            <RecipeDeskHomePage
                desk={
                    {
                        cards: undefined,
                        feed: undefined,
                        liveCount: undefined,
                        beatSpyCount: undefined,
                        medianReturnPct: undefined,
                    } as unknown as PublicDesk
                }
                onFork={vi.fn()}
            />,
        );

        expect(screen.getByText('No live recipes yet')).toBeInTheDocument();
    });
});

describe('normalizeLeaderboard', () => {
    it('treats an absent payload as an unknown board, not a young one', () => {
        expect(normalizeLeaderboard(undefined).degraded).toBe(true);
    });

    it('drops malformed chart points instead of passing junk through', () => {
        const board = normalizeLeaderboard({
            rows: [
                {
                    portfolioId: 'p1',
                    label: 'x',
                    returnPct: 1,
                    observations: 2,
                    series: [{ date: '2026-11-10', value: 'nope' }],
                },
            ],
        });

        expect(board.rows[0].series).toEqual([]);
        expect(board.degraded).toBe(false);
    });

    it('does not print NaN for a bad count or window', () => {
        const board = normalizeLeaderboard({ trackedCount: 'NaN', windowDays: 'NaN' });

        expect(board.trackedCount).toBeNull();
        expect(board.windowDays).toBe(30);
    });
});
