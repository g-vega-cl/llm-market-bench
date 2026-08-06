import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { fetchCauseAndEffectByEventId } from '../../cause-and-effect/api/fetch-cause-and-effect';
import { fetchChildResolutionEvent } from '../api/fetch-memories';
import type { Memory } from './MemoriesList';
import { MemoryCard } from './MemoryCard';

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        Link: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
            <a {...props}>{children}</a>
        ),
    };
});

vi.mock('../api/fetch-memories', async () => {
    const actual = await vi.importActual('../api/fetch-memories');
    return {
        ...actual,
        fetchChildResolutionEvent: vi.fn().mockResolvedValue(null),
    };
});

vi.mock('../../cause-and-effect/api/fetch-cause-and-effect', async () => {
    const actual = await vi.importActual('../../cause-and-effect/api/fetch-cause-and-effect');
    return {
        ...actual,
        fetchCauseAndEffectByEventId: vi.fn().mockResolvedValue(null),
    };
});

const createTestQueryClient = () =>
    new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    });

function renderWithClient(ui: React.ReactElement) {
    const client = createTestQueryClient();
    return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function makeMemory(overrides: Partial<Memory['metadata']> = {}): Memory {
    return {
        id: 'test-1',
        content: 'Fed signals potential rate cut in June',
        created_at: new Date().toISOString(),
        metadata: {
            type: 'consensus_event',
            impact: 'BULLISH',
            scenario_analysis:
                'Scenario A: 70% probability market rallies as rate cut boosts growth -> Trading Plan (How to Profit): Buy SPY. Scenario B: 30% probability stagflation fears cause sell-off -> Trading Plan (How to Profit): Buy GLD.',
            ...overrides,
        },
        status: 'ACTIVE',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        memory_type: 'MARKET_EVENT',
        importance_score: null,
        target_date: null,
    };
}

describe('MemoryCard scenario rendering', () => {
    it('does not show analysis section when no scenarios', () => {
        const memory = makeMemory();
        if (memory.metadata) {
            memory.metadata.scenarios = undefined;
            memory.metadata.scenario_analysis = undefined;
        }

        renderWithClient(<MemoryCard memory={memory} />);

        expect(screen.queryByText('Show Analysis')).not.toBeInTheDocument();
    });

    it('renders explicit scenarios with nested tickers from metadata.scenarios', () => {
        const memory = makeMemory();
        memory.metadata = {
            type: 'consensus_event',
            impact: 'BULLISH',
            scenarios: [
                {
                    cleanHeader: 'Scenario A: Cut',
                    percentage: '70%',
                    outcome: 'Rallies as rate cut boosts growth',
                    tradingPlan: 'Buy SPY and growth stocks',
                    assets: [
                        {
                            ticker: 'SPY',
                            name: 'SPDR S&P 500 ETF Trust',
                            reason: 'Broad market ETF',
                        },
                    ],
                },
                {
                    cleanHeader: 'Scenario B: Hold',
                    percentage: '30%',
                    outcome: 'Stagflation fears cause sell-off',
                    tradingPlan: 'Buy GLD safe haven',
                    assets: [{ ticker: 'GLD', name: 'SPDR Gold Shares', reason: 'Gold hedge' }],
                },
            ],
        };

        renderWithClient(<MemoryCard memory={memory} />);

        fireEvent.click(screen.getByText('Show Analysis'));

        expect(screen.getByText('Scenario A: Cut')).toBeInTheDocument();
        expect(screen.getByText('Scenario B: Hold')).toBeInTheDocument();
        expect(screen.getByText('$SPY')).toBeInTheDocument();
        expect(screen.getByText('$GLD')).toBeInTheDocument();
    });

    it('does not show Other Investable Assets section if all assets are mapped to scenarios', () => {
        const memory = makeMemory();
        memory.metadata = {
            type: 'consensus_event',
            impact: 'BULLISH',
            scenario_analysis: 'Investable Assets: ...',
            scenarios: [
                {
                    cleanHeader: 'Scenario A: Cut',
                    percentage: '70%',
                    outcome: 'Rallies as rate cut boosts growth',
                    tradingPlan: 'Buy SPY and growth stocks',
                    assets: [
                        {
                            ticker: 'SPY',
                            name: 'SPDR S&P 500 ETF Trust',
                            reason: 'Broad market ETF',
                        },
                    ],
                },
            ],
            discovered_assets: [
                {
                    ticker: 'SPY',
                    name: 'SPDR S&P 500 ETF Trust',
                    reason: 'Broad market ETF',
                },
            ],
        };

        renderWithClient(<MemoryCard memory={memory} />);
        fireEvent.click(screen.getByText('Show Analysis'));

        expect(screen.queryByText('Other Investable Assets')).not.toBeInTheDocument();
    });

    it('renders child resolution event details and cause-and-effect market outcomes when parent memory is resolved', async () => {
        const memory = makeMemory();
        memory.status = 'RESOLVED';

        const mockChildEvent: Memory = {
            id: 'child-1',
            content:
                'MARKET EVENT: US-Iran 14-Point MOU Signing [ONGOING] | SUMMARY: Geopolitical premium evaporates...',
            created_at: new Date().toISOString(),
            metadata: { type: 'consensus_event', impact: 'NEUTRAL' },
            status: 'RESOLVED',
            parent_id: 'test-1',
            relationship_type: 'RESOLUTION',
            relevance_score: null,
            memory_type: 'MARKET_EVENT',
            importance_score: null,
            target_date: null,
        };

        const mockCausalOutcome = {
            id: 'causal-1',
            event_id: 'child-1',
            market_outcome:
                'Energy assets (XOM) corrected lower while broad market sentiment stabilized',
            analysis:
                'The Strait of Hormuz ceasefire served as a definitive geopolitical de-escalation signal...',
            confidence: 85,
            tags: ['energy-prices', 'geopolitics'],
            created_at: new Date().toISOString(),
        };

        vi.mocked(fetchChildResolutionEvent).mockResolvedValue(mockChildEvent);
        vi.mocked(fetchCauseAndEffectByEventId).mockImplementation(async (eventId) => {
            if (eventId === 'child-1') {
                return mockCausalOutcome;
            }
            return null;
        });

        renderWithClient(<MemoryCard memory={memory} />);
        fireEvent.click(screen.getByText('Show Analysis'));

        await waitFor(() => {
            expect(screen.getByText(/Resolution & Market Performance/i)).toBeInTheDocument();
            expect(screen.getByText(/Resolved by:/i)).toBeInTheDocument();

            const childResolutions = screen.getAllByText(/US-Iran 14-Point MOU/i);
            expect(childResolutions.length).toBeGreaterThan(0);

            expect(screen.getByText(/Energy assets \(XOM\) corrected lower/i)).toBeInTheDocument();
            expect(screen.getByText(/The Strait of Hormuz ceasefire/i)).toBeInTheDocument();
            expect(screen.getByText(/Confidence: 85%/i)).toBeInTheDocument();
            expect(screen.getByText(/energy-prices/i)).toBeInTheDocument();
        });
    });

    it('renders similarity match badge when similarity is present', () => {
        const memory = makeMemory();
        memory.similarity = 0.84;

        renderWithClient(<MemoryCard memory={memory} />);

        expect(screen.getByText('Match: 84%')).toBeInTheDocument();
    });

    it('identifies and highlights winning scenario and resolution details when card is resolved', async () => {
        const memory = makeMemory();
        memory.status = 'RESOLVED';
        memory.metadata = {
            winning_scenario: 'Scenario A: Rates Cut',
            scenarios: [
                {
                    cleanHeader: 'Scenario A: Rates Cut',
                    percentage: '70%',
                    outcome: 'Fed cuts rates by 50bps, markets rally.',
                    tradingPlan: 'Buy SPY and QQQ.',
                },
                {
                    cleanHeader: 'Scenario B: Rates Hold',
                    percentage: '30%',
                    outcome: 'Fed holds rates, market consolidates.',
                    tradingPlan: 'Hold cash.',
                },
            ],
        };

        const mockCausalOutcome = {
            id: 'causal-1',
            event_id: 'test-1',
            market_outcome: 'Fed executed 50bps cut matching Scenario A',
            analysis: 'Economic data aligned with dovish projections.',
            confidence: 90,
            tags: ['fed', 'interest-rates'],
            created_at: new Date().toISOString(),
        };

        vi.mocked(fetchChildResolutionEvent).mockResolvedValue(null);
        vi.mocked(fetchCauseAndEffectByEventId).mockImplementation(async (eventId) => {
            if (eventId === 'test-1') {
                return mockCausalOutcome;
            }
            return null;
        });

        renderWithClient(<MemoryCard memory={memory} />);

        // Should render unexpanded winning scenario badge
        expect(screen.getByText(/Winning Scenario: Scenario A: Rates Cut/i)).toBeInTheDocument();

        // Expand analysis
        fireEvent.click(screen.getByText('Show Analysis'));

        await waitFor(() => {
            expect(screen.getAllByText(/WINNING SCENARIO/i).length).toBeGreaterThan(0);
            expect(
                screen.getByText(/Fed executed 50bps cut matching Scenario A/i),
            ).toBeInTheDocument();
            expect(screen.getByText(/What Resolved:/i)).toBeInTheDocument();
            expect(screen.getByText(/Why It Resolved/i)).toBeInTheDocument();
        });
    });
});
