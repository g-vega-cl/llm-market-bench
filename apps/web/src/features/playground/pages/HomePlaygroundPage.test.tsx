import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { normalizeMood } from '../lib/mood';
import { pickProof } from '../lib/proof';
import { HomePlaygroundPage } from './HomePlaygroundPage';

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children }: { children: React.ReactNode }) => <a href="#test">{children}</a>,
    useRouter: () => ({ navigate: vi.fn() }),
}));
vi.mock('@posthog/react', () => ({ usePostHog: () => null }));
vi.mock('../api/launch-recipe', () => ({ launchRecipeFn: vi.fn() }));
vi.mock('../api/run-requests', () => ({ submitRunRequestFn: vi.fn() }));
vi.mock('~/features/recipes/builder/compiler-api', () => ({ compileStrategyFn: vi.fn() }));
// The world needs WebGL; this page test is about copy and structure.
vi.mock('../components/VoxelWorld', () => ({ VoxelWorld: () => <div data-testid="world" /> }));

const desk = {
    cards: [],
    feed: [],
    liveCount: 2,
    beatSpyCount: 1,
    medianReturnPct: -0.5,
    spotlight: null,
};

const leaderboard = {
    rows: [
        {
            portfolioId: 'a',
            label: 'Alpha',
            returnPct: 4.2,
            observations: 10,
            series: [{ date: '2026-11-19', value: 1 }],
        },
    ],
    worst: {
        portfolioId: 'z',
        label: 'Zulu',
        returnPct: -6.4,
        observations: 10,
        series: [],
    },
    spy: [],
    medianReturnPct: -0.5,
    trackedCount: 9,
    windowDays: 30,
    degraded: false,
    spyUnavailable: false,
};

function renderPage(runsLeft: number | null = 2) {
    return render(
        <HomePlaygroundPage
            mood={normalizeMood({
                market_direction: 'BULLISH',
                confidence_score: 78,
                created_at: new Date().toISOString(),
            })}
            proof={pickProof(leaderboard as never)}
            desk={desk as never}
            isAuthenticated={false}
            runsLeft={runsLeft}
        />,
    );
}

describe('HomePlaygroundPage', () => {
    it('leads with the builder, not the board', () => {
        renderPage();
        expect(screen.getByRole('heading', { level: 1 }).textContent).toMatch(/Stack five blocks/);
        expect(screen.getAllByTestId(/^block-/).length).toBeGreaterThanOrEqual(4);
    });

    it('states the market reading in words, not only in colour', () => {
        renderPage();
        expect(screen.getByText(/Desk reads bullish, 78% confidence/)).toBeInTheDocument();
    });

    it('publishes a loser beside the winner', () => {
        renderPage();
        expect(screen.getByText(/Best:/)).toBeInTheDocument();
        expect(screen.getByText(/Worst:/)).toBeInTheDocument();
        expect(screen.getByText('Zulu')).toBeInTheDocument();
    });

    it('offers the request form up front when the visitor is already out of runs', () => {
        renderPage(0);
        expect(screen.getByRole('button', { name: /ask for more runs/i })).toBeInTheDocument();
    });

    it('does not show the request form while runs remain', () => {
        renderPage(2);
        expect(
            screen.queryByRole('button', { name: /ask for more runs/i }),
        ).not.toBeInTheDocument();
    });
});
