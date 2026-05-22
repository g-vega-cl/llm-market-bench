import { render, screen } from '@testing-library/react';
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
    UncorrelatedPairs: () => <div data-testid="uncorrelated-pairs">Mock Uncorrelated Pairs</div>,
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
});
