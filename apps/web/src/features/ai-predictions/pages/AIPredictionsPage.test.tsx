import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { SectorPrediction } from '../api/fetch-predictions';
import { AIPredictionsPage } from './AIPredictionsPage';

describe('AIPredictionsPage', () => {
    const mockPredictions: SectorPrediction[] = [
        {
            id: 'pred-pending-1',
            prediction_date: '2026-07-19T00:00:00Z',
            target_date: '2026-07-26T00:00:00Z',
            timeframe: '7d',
            model_name: 'deepseek-flash',
            prompt_tag: 'v1.0',
            predicted_sector: 'XLK',
            predicted_pair: ['GLD', 'XLU'],
            reasoning: 'Strong tech momentum expected ahead of earnings.',
            sector_percentile_score: null,
            pair_percentile_score: null,
            predicted_sector_return: null,
            predicted_pair_return: null,
            benchmark_spy_return: null,
            evaluation_audit_data: null,
            status: 'pending',
            created_at: '2026-07-19T00:00:00Z',
        },
        {
            id: 'pred-eval-1',
            prediction_date: '2026-07-10T00:00:00Z',
            target_date: '2026-07-17T00:00:00Z',
            timeframe: '7d',
            model_name: 'deepseek-flash',
            prompt_tag: 'v1.0',
            predicted_sector: 'XLK',
            predicted_pair: ['GLD', 'XLU'],
            reasoning: 'Semiconductor tailwinds.',
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
            id: 'pred-eval-2',
            prediction_date: '2026-07-10T00:00:00Z',
            target_date: '2026-07-17T00:00:00Z',
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
            created_at: '2026-07-10T00:00:00Z',
        },
        {
            id: 'pred-eval-3',
            prediction_date: '2026-07-10T00:00:00Z',
            target_date: '2026-07-17T00:00:00Z',
            timeframe: '7d',
            model_name: 'gemini-3.5-flash-lite',
            prompt_tag: 'v1.0',
            predicted_sector: 'XLF',
            predicted_pair: ['XLF', 'KRE'],
            reasoning: 'Banking sector resilience.',
            sector_percentile_score: 80.0,
            pair_percentile_score: 70.0,
            predicted_sector_return: 2.5,
            predicted_pair_return: 1.5,
            benchmark_spy_return: 1.8,
            evaluation_audit_data: null,
            status: 'evaluated',
            created_at: '2026-07-10T00:00:00Z',
        },
        {
            id: 'pred-eval-4',
            prediction_date: '2026-07-10T00:00:00Z',
            target_date: '2026-07-17T00:00:00Z',
            timeframe: '7d',
            model_name: 'gpt-5.6-luna',
            prompt_tag: 'v1.0',
            predicted_sector: 'XLV',
            predicted_pair: ['XLV', 'XBI'],
            reasoning: 'Healthcare biotech rotation.',
            sector_percentile_score: 88.0,
            pair_percentile_score: 82.0,
            predicted_sector_return: 3.1,
            predicted_pair_return: 2.8,
            benchmark_spy_return: 1.8,
            evaluation_audit_data: null,
            status: 'evaluated',
            created_at: '2026-07-10T00:00:00Z',
        },
    ];

    const mockExperiments: PromptExperiment[] = [
        {
            id: 'exp-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'v1.0',
            experiment_type: 'baseline',
            prompt_content: 'Predict top sector.',
            change_description: 'Initial baseline.',
            metrics: { score: 85.0 },
            status: 'active',
            week_start: '2026-07-10',
            week_end: '2026-07-17',
            created_at: '2026-07-10T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: null,
        },
    ];

    const refreshFn = vi.fn().mockResolvedValue({
        predictions: mockPredictions,
        experiments: mockExperiments,
    });

    it('renders historical performance chart at the top of the dashboard', () => {
        render(
            <AIPredictionsPage
                initialData={mockPredictions}
                experiments={mockExperiments}
                refreshFn={refreshFn}
            />,
        );

        expect(screen.getByText('Historical Accuracy Trend')).toBeInTheDocument();
        expect(screen.getByRole('img', { name: /AI Prediction Chart/i })).toBeInTheDocument();
    });

    it('filters predictions by status (Active vs Past Outcomes vs All)', () => {
        render(
            <AIPredictionsPage
                initialData={mockPredictions}
                experiments={mockExperiments}
                refreshFn={refreshFn}
            />,
        );

        // Switch to Feed Cards view
        fireEvent.click(screen.getByRole('button', { name: /Feed Cards/i }));

        expect(
            screen.getByText('Strong tech momentum expected ahead of earnings.'),
        ).toBeInTheDocument();
        expect(screen.getByText('Semiconductor tailwinds.')).toBeInTheDocument();

        const activeFilterBtn = screen.getByRole('button', { name: /Active \(1\)/i });
        fireEvent.click(activeFilterBtn);

        expect(
            screen.getByText('Strong tech momentum expected ahead of earnings.'),
        ).toBeInTheDocument();
        expect(screen.queryByText('Semiconductor tailwinds.')).not.toBeInTheDocument();

        const pastFilterBtn = screen.getByRole('button', { name: /Past Outcomes \(4\)/i });
        fireEvent.click(pastFilterBtn);

        expect(
            screen.queryByText('Strong tech momentum expected ahead of earnings.'),
        ).not.toBeInTheDocument();
        expect(screen.getByText('Semiconductor tailwinds.')).toBeInTheDocument();
    });

    it('displays S&P 500 benchmark performance comparison and alpha vs S&P', () => {
        render(
            <AIPredictionsPage
                initialData={mockPredictions}
                experiments={mockExperiments}
                refreshFn={refreshFn}
            />,
        );

        // Switch to Feed Cards view
        fireEvent.click(screen.getByRole('button', { name: /Feed Cards/i }));

        expect(screen.getAllByText(/Prediction vs S&P 500 Benchmark/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/S&P 500 \(SPY\): \+1.8%/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/\+2.4% vs S&P 500/i)).toBeInTheDocument();
    });

    it('renders Data Audit & Price Verification drawer with start/end prices and verification dates', () => {
        render(
            <AIPredictionsPage
                initialData={mockPredictions}
                experiments={mockExperiments}
                refreshFn={refreshFn}
            />,
        );

        // Switch to Feed Cards view
        fireEvent.click(screen.getByRole('button', { name: /Feed Cards/i }));

        expect(screen.getByText(/Data Audit & Price Verification/i)).toBeInTheDocument();
        expect(screen.getByText(/\$542\.10 ➔ \$551\.86/i)).toBeInTheDocument();
        expect(screen.getByText(/\$210\.50 ➔ \$219\.34/i)).toBeInTheDocument();
    });

    it('calculates and displays head-to-head model performance metrics for all 4 models', () => {
        render(
            <AIPredictionsPage
                initialData={mockPredictions}
                experiments={mockExperiments}
                refreshFn={refreshFn}
            />,
        );

        expect(screen.getAllByText('DeepSeek Models').length).toBeGreaterThan(0);
        expect(screen.getAllByText('MiniMax-M3').length).toBeGreaterThan(0);
        expect(screen.getAllByText('Gemini 3.5').length).toBeGreaterThan(0);
        expect(screen.getAllByText('OpenAI GPT-5.6').length).toBeGreaterThan(0);
    });
});
