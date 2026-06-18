import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
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
});
