import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { DailyStockBasket } from '../api/fetch-stock-picks';
import { DailyStockPicksTab } from './DailyStockPicksTab';

describe('DailyStockPicksTab', () => {
    const mockBaskets: DailyStockBasket[] = [
        {
            id: 'basket-1',
            target_date: '2026-11-11',
            model_name: 'consensus',
            status: 'evaluated',
            directional_hit_rate: 83.3,
            mean_long_return_pct: 1.85,
            mean_short_return_pct: -0.62,
            ls_spread_alpha_pct: 2.47,
            excess_alpha_vs_spy_pct: 1.5,
            benchmark_spy_return_pct: 0.97,
            created_at: '2026-11-11T14:00:00Z',
            evaluated_at: '2026-11-11T21:05:00Z',
            picks: [
                {
                    id: 'pick-u1',
                    basket_id: 'basket-1',
                    target_date: '2026-11-11',
                    model_name: 'consensus',
                    ticker: 'CB',
                    direction: 'UP',
                    rank: 1,
                    confidence: 73.0,
                    expected_return_pct: 1.8,
                    reasoning: 'Float income expansion under elevated yields.',
                    status: 'evaluated',
                    open_price: 360.0,
                    close_price: 366.5,
                    stock_return_pct: 1.81,
                    position_return_pct: 1.81,
                    is_hit: true,
                    conviction_points: 65.0,
                    created_at: '2026-11-11T14:00:00Z',
                    evaluated_at: '2026-11-11T21:05:00Z',
                },
                {
                    id: 'pick-u2',
                    basket_id: 'basket-1',
                    target_date: '2026-11-11',
                    model_name: 'consensus',
                    ticker: 'ETR',
                    direction: 'UP',
                    rank: 2,
                    confidence: 71.0,
                    expected_return_pct: 1.5,
                    reasoning: 'Regulated utility secular AI data center power demand.',
                    status: 'evaluated',
                    open_price: 110.0,
                    close_price: 112.2,
                    stock_return_pct: 2.0,
                    position_return_pct: 2.0,
                    is_hit: true,
                    conviction_points: 62.0,
                    created_at: '2026-11-11T14:00:00Z',
                    evaluated_at: '2026-11-11T21:05:00Z',
                },
                {
                    id: 'pick-u3',
                    basket_id: 'basket-1',
                    target_date: '2026-11-11',
                    model_name: 'consensus',
                    ticker: 'TSM',
                    direction: 'UP',
                    rank: 3,
                    confidence: 69.0,
                    expected_return_pct: 2.1,
                    reasoning: 'Approved $1B strategic AI investments.',
                    status: 'evaluated',
                    open_price: 400.0,
                    close_price: 407.0,
                    stock_return_pct: 1.75,
                    position_return_pct: 1.75,
                    is_hit: true,
                    conviction_points: 58.0,
                    created_at: '2026-11-11T14:00:00Z',
                    evaluated_at: '2026-11-11T21:05:00Z',
                },
                {
                    id: 'pick-d1',
                    basket_id: 'basket-1',
                    target_date: '2026-11-11',
                    model_name: 'consensus',
                    ticker: 'ABNB',
                    direction: 'DOWN',
                    rank: 1,
                    confidence: 78.0,
                    expected_return_pct: -2.4,
                    reasoning: 'Consumer credit stress and multiple compression.',
                    status: 'evaluated',
                    open_price: 195.0,
                    close_price: 191.1,
                    stock_return_pct: -2.0,
                    position_return_pct: 2.0,
                    is_hit: true,
                    conviction_points: 71.0,
                    created_at: '2026-11-11T14:00:00Z',
                    evaluated_at: '2026-11-11T21:05:00Z',
                },
                {
                    id: 'pick-d2',
                    basket_id: 'basket-1',
                    target_date: '2026-11-11',
                    model_name: 'consensus',
                    ticker: 'NVDA',
                    direction: 'DOWN',
                    rank: 2,
                    confidence: 68.0,
                    expected_return_pct: -1.9,
                    reasoning: 'Export control overhang and high realized volatility breakdown.',
                    status: 'evaluated',
                    open_price: 175.0,
                    close_price: 172.0,
                    stock_return_pct: -1.71,
                    position_return_pct: 1.71,
                    is_hit: true,
                    conviction_points: 60.0,
                    created_at: '2026-11-11T14:00:00Z',
                    evaluated_at: '2026-11-11T21:05:00Z',
                },
                {
                    id: 'pick-d3',
                    basket_id: 'basket-1',
                    target_date: '2026-11-11',
                    model_name: 'consensus',
                    ticker: 'GOOGL',
                    direction: 'DOWN',
                    rank: 3,
                    confidence: 64.0,
                    expected_return_pct: -1.2,
                    reasoning: 'Heavy duration discount-rate headwinds.',
                    status: 'evaluated',
                    open_price: 290.0,
                    close_price: 295.0,
                    stock_return_pct: 1.72,
                    position_return_pct: -1.72,
                    is_hit: false,
                    conviction_points: 38.0,
                    created_at: '2026-11-11T14:00:00Z',
                    evaluated_at: '2026-11-11T21:05:00Z',
                },
            ],
        },
    ];

    it('renders empty state when no baskets exist', () => {
        render(<DailyStockPicksTab baskets={[]} />);
        expect(
            screen.getByText('No active stock picks found for selected model track.'),
        ).toBeInTheDocument();
    });

    it('renders 3 UP and 3 DOWN picks with confidence and ticker', () => {
        render(<DailyStockPicksTab baskets={mockBaskets} />);

        // Long picks
        expect(screen.getByText('CB')).toBeInTheDocument();
        expect(screen.getByText('ETR')).toBeInTheDocument();
        expect(screen.getByText('TSM')).toBeInTheDocument();

        // Short picks
        expect(screen.getByText('ABNB')).toBeInTheDocument();
        expect(screen.getByText('NVDA')).toBeInTheDocument();
        expect(screen.getByText('GOOGL')).toBeInTheDocument();

        // Direction labels
        expect(screen.getByText(/3 Stocks To Go UP/)).toBeInTheDocument();
        expect(screen.getByText(/3 Stocks To Go DOWN/)).toBeInTheDocument();

        // Metrics
        expect(screen.getAllByText('83.3%').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('+2.47%').length).toBeGreaterThanOrEqual(1);
    });

    it('switches model filter tabs when clicked', () => {
        render(<DailyStockPicksTab baskets={mockBaskets} />);

        const deepseekBtn = screen.getByRole('button', { name: /DeepSeek Flash/i });
        fireEvent.click(deepseekBtn);

        // Since mockBaskets only has consensus, switching to DeepSeek shows empty state
        expect(
            screen.getByText('No active stock picks found for selected model track.'),
        ).toBeInTheDocument();
    });
});
