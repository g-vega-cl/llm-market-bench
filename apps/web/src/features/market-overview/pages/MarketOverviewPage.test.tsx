import { fireEvent, render, screen } from '@testing-library/react';
import type * as React from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { MarketOverviewData } from '../api/fetch-market-overview';
import { MarketOverviewPage } from './MarketOverviewPage';

// Mock Tanstack Query's useSuspenseQuery to return the data directly
vi.mock('@tanstack/react-query', async (importOriginal) => {
    const original = await importOriginal<typeof import('@tanstack/react-query')>();
    return {
        ...original,
        useSuspenseQuery: vi.fn().mockImplementation(({ initialData }) => ({
            data: initialData,
        })),
    };
});

// Mock the Link component from Tanstack Router so we don't need a router context
vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

// Mock custom components that might perform API queries or need extra context
vi.mock('../components/CorrelationHeatmap', () => ({
    CorrelationHeatmap: () => <div data-testid="correlation-heatmap">Mock Heatmap</div>,
}));
vi.mock('../components/UncorrelatedPairs', () => ({
    UncorrelatedPairs: ({ onSelectPair }: { onSelectPair?: (a: string, b: string) => void }) => (
        <div data-testid="uncorrelated-pairs">
            Mock Uncorrelated Pairs
            {onSelectPair && (
                <button
                    type="button"
                    data-testid="mock-history-btn"
                    onClick={() => onSelectPair('BTCUSD', 'ETHUSD')}
                >
                    View History
                </button>
            )}
        </div>
    ),
}));
vi.mock('../components/CorrelationHistoryExplorer', () => ({
    CorrelationHistoryExplorer: ({
        tickers,
        initialPair,
    }: {
        tickers: string[];
        initialPair?: { tickerA: string; tickerB: string } | null;
    }) => (
        <div data-testid="history-explorer">
            Mock History Explorer: {tickers.join(',')}
            {initialPair && (
                <span data-testid="initial-pair">
                    {initialPair.tickerA}/{initialPair.tickerB}
                </span>
            )}
        </div>
    ),
}));

describe('MarketOverviewPage', () => {
    it('should render CPER in the Sector Performance Grid within the Commodities section', () => {
        const mockData = {
            correlationRun: {
                id: 'run-123',
                run_date: '2026-05-18T16:00:00Z',
                created_at: '2026-05-18T16:00:00Z',
                window_days: 90,
                num_assets: 5,
                tickers: ['GLD', 'SLV', 'PDBC', 'USO', 'CPER'],
            },
            correlationData: [
                {
                    id: '1',
                    run_id: 'run-123',
                    ticker_a: 'GLD',
                    ticker_b: 'SLV',
                    pearson_corr: 0.8,
                    spearman_corr: 0.8,
                    returns_a_90d: 0.05,
                    returns_b_90d: 0.03,
                    data_points: 60,
                },
                {
                    id: '2',
                    run_id: 'run-123',
                    ticker_a: 'SLV',
                    ticker_b: 'GLD',
                    pearson_corr: 0.8,
                    spearman_corr: 0.8,
                    returns_a_90d: 0.03,
                    returns_b_90d: 0.05,
                    data_points: 60,
                },
                {
                    id: '3',
                    run_id: 'run-123',
                    ticker_a: 'PDBC',
                    ticker_b: 'GLD',
                    pearson_corr: 0.4,
                    spearman_corr: 0.4,
                    returns_a_90d: -0.02,
                    returns_b_90d: 0.05,
                    data_points: 60,
                },
                {
                    id: '4',
                    run_id: 'run-123',
                    ticker_a: 'USO',
                    ticker_b: 'GLD',
                    pearson_corr: 0.3,
                    spearman_corr: 0.3,
                    returns_a_90d: 0.08,
                    returns_b_90d: 0.05,
                    data_points: 60,
                },
                {
                    id: '5',
                    run_id: 'run-123',
                    ticker_a: 'CPER',
                    ticker_b: 'GLD',
                    pearson_corr: 0.5,
                    spearman_corr: 0.5,
                    returns_a_90d: 0.12,
                    returns_b_90d: 0.05,
                    data_points: 60,
                },
            ],
            marketFeeling: {
                id: 'feeling-123',
                created_at: '2026-05-18T16:00:00Z',
                feeling: 'BULLISH',
                confidence: 80,
                sentiment_emoji: '🐂',
                sentiment_label: 'Bullish Sentiment',
                market_direction: 'BULLISH',
                confidence_score: 80,
                why_explanation: 'Strong performance in large caps.',
                primary_concern: 'Inflation',
                model_used: 'gemini-2.5-pro',
            },
        } as unknown as MarketOverviewData;

        render(<MarketOverviewPage initialData={mockData} fetchFn={async () => mockData} />);

        // Expect CPER to be rendered on the page in the Commodities section
        expect(screen.getByText('CPER')).toBeInTheDocument();
    });

    it('supports tabbed navigation between current regime and historical progression', () => {
        const mockData = {
            correlationRun: {
                id: 'run-123',
                run_date: '2026-05-18T16:00:00Z',
                created_at: '2026-05-18T16:00:00Z',
                window_days: 90,
                num_assets: 2,
                tickers: ['BTCUSD', 'ETHUSD'],
            },
            correlationData: [],
            marketFeeling: null,
        } as unknown as MarketOverviewData;

        render(<MarketOverviewPage initialData={mockData} fetchFn={async () => mockData} />);

        // By default, current regime components are rendered (e.g. heatmap and uncorrelated pairs)
        expect(screen.getByTestId('correlation-heatmap')).toBeInTheDocument();
        expect(screen.getByTestId('uncorrelated-pairs')).toBeInTheDocument();
        expect(screen.queryByTestId('history-explorer')).not.toBeInTheDocument();

        // Switch to history tab
        const historyTabButton = screen.getByRole('button', { name: /historical progression/i });
        fireEvent.click(historyTabButton);

        // Now, history explorer is rendered and current regime is hidden
        expect(screen.queryByTestId('correlation-heatmap')).not.toBeInTheDocument();
        expect(screen.queryByTestId('uncorrelated-pairs')).not.toBeInTheDocument();
        expect(screen.getByTestId('history-explorer')).toBeInTheDocument();
        expect(screen.getByTestId('history-explorer')).toHaveTextContent('BTCUSD,ETHUSD');

        // Switch back to current regime
        const currentTabButton = screen.getByRole('button', { name: /current regime/i });
        fireEvent.click(currentTabButton);

        expect(screen.getByTestId('correlation-heatmap')).toBeInTheDocument();
        expect(screen.queryByTestId('history-explorer')).not.toBeInTheDocument();
    });

    it('navigates and deep-links to history tab when View History is clicked in UncorrelatedPairs', () => {
        const mockData = {
            correlationRun: {
                id: 'run-123',
                run_date: '2026-05-18T16:00:00Z',
                created_at: '2026-05-18T16:00:00Z',
                window_days: 90,
                num_assets: 2,
                tickers: ['BTCUSD', 'ETHUSD'],
            },
            correlationData: [],
            marketFeeling: null,
        } as unknown as MarketOverviewData;

        render(<MarketOverviewPage initialData={mockData} fetchFn={async () => mockData} />);

        // Trigger onSelectPair callback in mocked UncorrelatedPairs
        const viewHistoryBtn = screen.getByTestId('mock-history-btn');
        fireEvent.click(viewHistoryBtn);

        // Active tab should automatically switch to history explorer
        expect(screen.queryByTestId('correlation-heatmap')).not.toBeInTheDocument();
        expect(screen.getByTestId('history-explorer')).toBeInTheDocument();

        // The selected pair should be passed down
        expect(screen.getByTestId('initial-pair')).toHaveTextContent('BTCUSD/ETHUSD');
    });
});
