import { render, screen, waitFor } from '@testing-library/react';
import type * as React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { CorrelationHistoryExplorer } from './CorrelationHistoryExplorer';

// Mock Tanstack Router
vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

// Mock the progression chart to avoid D3 SVG rendering complex structures in JSDOM
vi.mock('./PairProgressionChart', () => ({
    PairProgressionChart: ({ data }: { data: unknown[] }) => (
        <div data-testid="pair-progression-chart">Chart with {data.length} points</div>
    ),
}));

describe('CorrelationHistoryExplorer', () => {
    const mockTickers = ['BTCUSD', 'ETHUSD', 'SPY', 'TLT', 'GLD'];

    it('renders placeholder state when no tickers are selected', () => {
        render(<CorrelationHistoryExplorer tickers={mockTickers} initialPair={null} />);

        expect(
            screen.getByText(/Select an asset pair to view historical progression/i),
        ).toBeInTheDocument();
    });

    it('renders the asset selection controls and jumps', () => {
        render(<CorrelationHistoryExplorer tickers={mockTickers} initialPair={null} />);

        // Verify quick-jump buttons
        expect(screen.getByText(/Crypto Decoupling/i)).toBeInTheDocument();
        expect(screen.getByText(/Equities vs Bonds/i)).toBeInTheDocument();
    });

    it('renders the asset selection options with full ETF descriptions', () => {
        render(<CorrelationHistoryExplorer tickers={mockTickers} initialPair={null} />);

        // Verify select dropdowns contain the descriptions
        const optionBTC = screen.getAllByRole('option', { name: /BTCUSD — Bitcoin to USD/i });
        const optionSPY = screen.getAllByRole('option', { name: /SPY — SPDR S&P 500 ETF Trust/i });

        expect(optionBTC.length).toBe(2); // One for select A, one for select B
        expect(optionSPY.length).toBe(2);
    });

    it('should call fetch function and render chart when selectors are updated', async () => {
        const mockFetchHistory = vi.fn().mockResolvedValue([
            {
                run_date: '2026-05-10',
                pearson_corr: 0.85,
                spearman_corr: 0.82,
                returns_a_90d: 12.5,
                returns_b_90d: 10.2,
            },
            {
                run_date: '2026-05-17',
                pearson_corr: 0.75,
                spearman_corr: 0.71,
                returns_a_90d: 8.4,
                returns_b_90d: 5.6,
            },
        ]);

        render(
            <CorrelationHistoryExplorer
                tickers={mockTickers}
                initialPair={{ tickerA: 'BTCUSD', tickerB: 'ETHUSD' }}
                onFetchHistory={mockFetchHistory}
            />,
        );

        // Wait for the mock fetch to be called
        await waitFor(() => {
            expect(mockFetchHistory).toHaveBeenCalledWith('BTCUSD', 'ETHUSD');
        });

        // Verify the chart was rendered with the loaded data points
        await waitFor(() => {
            expect(screen.getByTestId('pair-progression-chart')).toHaveTextContent(
                'Chart with 2 points',
            );
        });
    });
});
