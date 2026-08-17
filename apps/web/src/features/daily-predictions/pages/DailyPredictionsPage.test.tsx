import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { DailyPredictionsPage } from './DailyPredictionsPage';

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        style,
    }: {
        children: React.ReactNode;
        to: string;
        style?: React.CSSProperties;
    }) => (
        <a href={to} style={style}>
            {children}
        </a>
    ),
}));

describe('DailyPredictionsPage', () => {
    const mockPredictions: DailyPrediction[] = [
        {
            id: 'daily-pred-deepseek-1',
            prediction_date: '2026-08-03',
            target_date: '2026-08-03',
            ticker: 'SPY',
            model_name: 'deepseek-v4-flash',
            prompt_variant_tag: 'daily-active-1',
            predicted_direction: 'UP',
            confidence: 80.0,
            expected_return_pct: 0.45,
            rationale: 'Overnight futures momentum and strong earnings catalysts.',
            catalysts: ['Tech Earnings', 'Fed Stance'],
            open_price: 450.0,
            high_price: 456.0,
            low_price: 449.0,
            close_price: 455.0,
            actual_direction: 'UP',
            is_correct: true,
            intraday_hit: true,
            intraday_direction_hit: true,
            brier_score: 0.04,
            status: 'evaluated',
            created_at: '2026-08-03T08:00:00Z',
            updated_at: '2026-08-03T16:15:00Z',
        },
        {
            id: 'daily-pred-minimax-1',
            prediction_date: '2026-08-03',
            target_date: '2026-08-03',
            ticker: 'SPY',
            model_name: 'MiniMax-M3',
            prompt_variant_tag: 'daily-minimax-v1',
            predicted_direction: 'DOWN',
            confidence: 65.0,
            expected_return_pct: -0.35,
            rationale: 'Overextended technical indicators and upcoming CPI data.',
            catalysts: ['CPI Data'],
            open_price: 450.0,
            high_price: 456.0,
            low_price: 449.0,
            close_price: 455.0,
            actual_direction: 'UP',
            is_correct: false,
            intraday_hit: false,
            intraday_direction_hit: false,
            brier_score: 0.4225,
            status: 'evaluated',
            created_at: '2026-08-03T08:00:00Z',
            updated_at: '2026-08-03T16:15:00Z',
        },
    ];

    const mockExperiments: PromptExperiment[] = [
        {
            id: 'exp-daily-1',
            prompt_name: 'DAILY_PREDICTOR_PROMPT',
            variant_tag: 'daily-active-1',
            experiment_type: 'baseline',
            prompt_content: 'Analyze intraday S&P price action for DeepSeek.',
            change_description: 'Initial daily predictor baseline for DeepSeek.',
            metrics: { score: 75.0 },
            status: 'active',
            week_start: '2026-08-03',
            week_end: '2026-08-10',
            created_at: '2026-08-03T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'deepseek-v4-flash',
        },
        {
            id: 'exp-daily-2',
            prompt_name: 'DAILY_PREDICTOR_PROMPT',
            variant_tag: 'daily-minimax-v1',
            experiment_type: 'baseline',
            prompt_content: 'Analyze intraday S&P price action for MiniMax.',
            change_description: 'Initial daily predictor baseline for MiniMax.',
            metrics: { score: 55.0 },
            status: 'active',
            week_start: '2026-08-03',
            week_end: '2026-08-10',
            created_at: '2026-08-03T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'MiniMax-M3',
        },
    ];

    it('removes Refresh Data button and relocates Backtest Arena button to tab bar', () => {
        render(
            <DailyPredictionsPage
                initialPredictions={mockPredictions}
                experiments={mockExperiments}
            />,
        );

        expect(screen.queryByRole('button', { name: /Refresh Data/i })).not.toBeInTheDocument();
        const backtestLink = screen.getByRole('link', { name: /Backtest Arena/i });
        expect(backtestLink).toBeInTheDocument();
        expect(backtestLink.getAttribute('href')).toBe('/daily-predictions-backtest');
    });

    it('renders independent model tabs and defaults to first model (DeepSeek Flash)', () => {
        render(
            <DailyPredictionsPage
                initialPredictions={mockPredictions}
                experiments={mockExperiments}
            />,
        );

        expect(screen.getByText('Daily S&P Market Predictor')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /DeepSeek Flash/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /MiniMax M3/i })).toBeInTheDocument();

        // DeepSeek predictions shown
        expect(screen.getByText('▲ UP')).toBeInTheDocument();
        expect(screen.getByText('80% Confidence')).toBeInTheDocument();
        expect(
            screen.getByText(/Overnight futures momentum and strong earnings catalysts/i),
        ).toBeInTheDocument();

        // MiniMax rationale not shown on DeepSeek tab
        expect(
            screen.queryByText(/Overextended technical indicators and upcoming CPI data/i),
        ).not.toBeInTheDocument();
    });

    it('switches to MiniMax M3 tab and isolates MiniMax predictions, metrics, and hero card', () => {
        render(
            <DailyPredictionsPage
                initialPredictions={mockPredictions}
                experiments={mockExperiments}
            />,
        );

        const minimaxTabBtn = screen.getByRole('button', { name: /MiniMax M3/i });
        fireEvent.click(minimaxTabBtn);

        // MiniMax prediction now shown in hero and table
        expect(screen.getByText('▼ DOWN')).toBeInTheDocument();
        expect(screen.getByText('65% Confidence')).toBeInTheDocument();
        expect(
            screen.getByText(/Overextended technical indicators and upcoming CPI data/i),
        ).toBeInTheDocument();

        // DeepSeek rationale not shown on MiniMax tab
        expect(
            screen.queryByText(/Overnight futures momentum and strong earnings catalysts/i),
        ).not.toBeInTheDocument();
    });

    it('expands prediction row to display prompt variant content for active model', () => {
        render(
            <DailyPredictionsPage
                initialPredictions={mockPredictions}
                experiments={mockExperiments}
            />,
        );

        const expandBtn = screen.getByRole('button', { name: /View Details & Prompt/i });
        fireEvent.click(expandBtn);

        expect(
            screen.getByText(/Analyze intraday S&P price action for DeepSeek/i),
        ).toBeInTheDocument();
    });
});
