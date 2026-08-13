import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { SectorPrediction } from '../api/fetch-predictions';
import { AIPredictionsTable } from './AIPredictionsTable';

describe('AIPredictionsTable', () => {
    const mockPredictions: SectorPrediction[] = [
        {
            id: 'pred-1',
            prediction_date: '2026-07-20T00:00:00Z',
            target_date: '2026-07-27T00:00:00Z',
            timeframe: '7d',
            model_name: 'deepseek-flash',
            prompt_tag: 'v1.0',
            predicted_sector: 'XLK',
            predicted_pair: ['GLD', 'XLU'],
            reasoning: 'Bullish Tech momentum.',
            sector_percentile_score: null,
            pair_percentile_score: null,
            predicted_sector_return: null,
            predicted_pair_return: null,
            benchmark_spy_return: null,
            evaluation_audit_data: null,
            status: 'pending',
            created_at: '2026-07-20T00:00:00Z',
        },
        {
            id: 'pred-2',
            prediction_date: '2026-07-10T00:00:00Z',
            target_date: '2026-07-17T00:00:00Z',
            timeframe: '7d',
            model_name: 'deepseek-flash',
            prompt_tag: 'v1.0',
            predicted_sector: 'XLK',
            predicted_pair: ['GLD', 'XLU'],
            reasoning: 'Tech earnings rally.',
            sector_percentile_score: 92.5,
            pair_percentile_score: 85.0,
            predicted_sector_return: 4.2,
            predicted_pair_return: 2.1,
            benchmark_spy_return: 1.8,
            evaluation_audit_data: {
                start_date: '2026-07-10',
                end_date: '2026-07-17',
                spy: { ticker: 'SPY', start_price: 542.1, end_price: 551.86, return_pct: 1.8 },
                sector: { ticker: 'XLK', start_price: 210.5, end_price: 219.34, return_pct: 4.2 },
                pair: [
                    { ticker: 'GLD', start_price: 220.1, end_price: 224.5, return_pct: 2.0 },
                    { ticker: 'XLU', start_price: 68.4, end_price: 69.9, return_pct: 2.2 },
                ],
            },
            status: 'evaluated',
            created_at: '2026-07-10T00:00:00Z',
        },
        {
            id: 'pred-3',
            prediction_date: '2026-07-05T00:00:00Z',
            target_date: '2026-07-12T00:00:00Z',
            timeframe: '7d',
            model_name: 'MiniMax-M3',
            prompt_tag: 'v1.0',
            predicted_sector: 'XLE',
            predicted_pair: ['TLT', 'XLV'],
            reasoning: 'Energy supply tightness.',
            sector_percentile_score: 42.0,
            pair_percentile_score: 60.0,
            predicted_sector_return: -1.2,
            predicted_pair_return: 0.5,
            benchmark_spy_return: 1.8,
            evaluation_audit_data: null,
            status: 'evaluated',
            created_at: '2026-07-05T00:00:00Z',
        },
    ];

    it('renders key table headers and prediction details', () => {
        render(<AIPredictionsTable predictions={mockPredictions} />);

        expect(screen.getByText('Model & Prompt')).toBeInTheDocument();
        expect(screen.getByText('Prediction Date')).toBeInTheDocument();
        expect(screen.getByText('Target Date')).toBeInTheDocument();
        expect(screen.getByText('Predictions (Sector / Pair)')).toBeInTheDocument();
        expect(screen.getByText('Confidence')).toBeInTheDocument();
        expect(screen.getByText('Performance')).toBeInTheDocument();
        expect(screen.getByText('vs S&P 500 (Alpha)')).toBeInTheDocument();
        expect(screen.getByText('Brier Score')).toBeInTheDocument();

        // Check predictions presence
        expect(screen.getAllByText('XLK').length).toBeGreaterThan(0);
        expect(screen.getAllByText('GLD + XLU').length).toBeGreaterThan(0);
        expect(screen.getByText('XLE')).toBeInTheDocument();
        expect(screen.getByText('TLT + XLV')).toBeInTheDocument();
    });

    it('calculates performance vs S&P 500 (Alpha) correctly', () => {
        render(<AIPredictionsTable predictions={mockPredictions} />);

        // pred-2: sector return 4.2, SPY return 1.8 -> Alpha +2.40%
        expect(screen.getByText('+2.40%')).toBeInTheDocument();

        // pred-3: sector return -1.2, SPY return 1.8 -> Alpha -3.00%
        expect(screen.getByText('-3.00%')).toBeInTheDocument();
    });

    it('filters predictions by search query and model', () => {
        render(<AIPredictionsTable predictions={mockPredictions} />);

        const searchInput = screen.getByPlaceholderText('Search tickers, models, reasoning...');
        fireEvent.change(searchInput, { target: { value: 'MiniMax' } });

        expect(screen.getByText('XLE')).toBeInTheDocument();
        expect(screen.queryByText('GLD + XLU')).not.toBeInTheDocument();
    });

    it('toggles view mode between Dual, Sector Only, and Pair Only', () => {
        render(<AIPredictionsTable predictions={mockPredictions} />);

        const sectorOnlyBtn = screen.getByRole('button', { name: 'Single Sector' });
        fireEvent.click(sectorOnlyBtn);

        expect(screen.getByText('Sector Pick')).toBeInTheDocument();
        expect(screen.queryByText('Pair Combination')).not.toBeInTheDocument();

        const pairOnlyBtn = screen.getByRole('button', { name: 'Sector Pair' });
        fireEvent.click(pairOnlyBtn);

        expect(screen.getByText('Pair Combination')).toBeInTheDocument();
        expect(screen.queryByText('Sector Pick')).not.toBeInTheDocument();
    });

    it('expands row details on click to show audit prices and reasoning', () => {
        render(<AIPredictionsTable predictions={mockPredictions} />);

        const evalRow = screen.getAllByText('XLK')[1];
        fireEvent.click(evalRow);

        expect(screen.getByText('Reasoning & Market Audit')).toBeInTheDocument();
        expect(screen.getByText('Start: $210.50 ➔ End: $219.34')).toBeInTheDocument();
    });
});
