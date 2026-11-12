import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import type { BacktestResultData, RecipeAlert } from '../types';
import { RecipeAlertsInbox } from './RecipeAlertsInbox';
import { RecipeBacktestResults } from './RecipeBacktestResults';
import { RecipeFlowCanvas } from './RecipeFlowCanvas';
import { WaitlistPledgeModal } from './WaitlistPledgeModal';

describe('RecipeFlowCanvas', () => {
    it('renders all blocks from the starter recipe template', () => {
        const recipe = STARTER_RECIPES[0];
        const handleChange = vi.fn();

        render(<RecipeFlowCanvas recipe={recipe} onChange={handleChange} />);

        expect(screen.getByText('Pipeline Recipe Canvas')).toBeInTheDocument();
        expect(screen.getByText(/4 Blocks/i)).toBeInTheDocument();
        expect(screen.getByText('Semiconductor Headlines')).toBeInTheDocument();
        expect(screen.getByText('VWAP & RSI Filter')).toBeInTheDocument();
        expect(screen.getByText('Jev Catalyst Classifier')).toBeInTheDocument();
        expect(screen.getByText('Risk Guardrails')).toBeInTheDocument();
    });

    it('can add a new block to the pipeline', () => {
        const recipe = STARTER_RECIPES[0];
        const handleChange = vi.fn();

        render(<RecipeFlowCanvas recipe={recipe} onChange={handleChange} />);

        const addNewsBtn = screen.getByRole('button', { name: '+ News' });
        fireEvent.click(addNewsBtn);

        expect(handleChange).toHaveBeenCalled();
        const updatedRecipe = handleChange.mock.calls[0][0];
        expect(updatedRecipe.nodes.length).toBe(recipe.nodes.length + 1);
    });
});

describe('RecipeBacktestResults', () => {
    const mockResults: BacktestResultData = {
        starting_capital: 10000,
        ending_capital_midpoint: 10500,
        ending_capital_net: 10420,
        total_return_pct_midpoint: 5.0,
        total_return_pct_net: 4.2,
        total_trades: 10,
        winning_trades: 7,
        losing_trades: 3,
        win_rate_pct: 70.0,
        profit_factor: 2.5,
        max_drawdown_pct: 1.8,
        llm_calls_made: 4,
        equity_curve: [],
        trades: [],
        skipped_trades: [
            {
                time: '2026-03-02T15:00:00Z',
                reason: 'Technical gate blocked: price < vwap',
                skip_type: 'TECHNICAL_BLOCKED',
                headline: 'Tech sector catalyst headline',
            },
        ],
        weeks_breakdown: [
            {
                week: '2026-W10',
                trades_count: 10,
                week_pnl_midpoint: 500,
                week_pnl_net: 420,
            },
        ],
    };

    it('toggles between Net P&L and Midpoint P&L', () => {
        render(<RecipeBacktestResults results={mockResults} />);

        expect(screen.getByText('+4.20%')).toBeInTheDocument();

        const midpointBtn = screen.getByRole('button', { name: 'Midpoint (Zero-Cost)' });
        fireEvent.click(midpointBtn);

        expect(screen.getByText('+5.00%')).toBeInTheDocument();
    });

    it('renders counterfactual skipped trades list', () => {
        render(<RecipeBacktestResults results={mockResults} />);

        expect(screen.getByText(/Counterfactual Skipped Signals/i)).toBeInTheDocument();
        expect(screen.getByText('TECHNICAL_BLOCKED')).toBeInTheDocument();
        expect(screen.getByText('Technical gate blocked: price < vwap')).toBeInTheDocument();
    });

    it('safely renders weekly breakdown with backend pnl_net / trades keys without crashing', () => {
        const backendSchemaResults: BacktestResultData = {
            ...mockResults,
            weeks_breakdown: [
                {
                    week: '2026-W11',
                    trades: 8,
                    pnl_net: 310,
                },
            ],
        };
        render(<RecipeBacktestResults results={backendSchemaResults} />);
        expect(screen.getByText('2026-W11')).toBeInTheDocument();
        expect(screen.getByText('$310.00')).toBeInTheDocument();
    });
});

describe('RecipeAlertsInbox', () => {
    const mockAlerts: RecipeAlert[] = [
        {
            id: 'alert-1',
            user_id: 'usr-1',
            recipe_id: 'rec-1',
            recipe_name: 'NVDA VWAP Trend',
            ticker: 'NVDA',
            action: 'BUY',
            entry_price: 135.5,
            target_price: 139.5,
            stop_loss: 133.0,
            timeframe: '5m',
            reason: 'Session VWAP breakout on Rubin chip guidance',
            is_read: false,
            created_at: '2026-03-02T14:35:00Z',
        },
    ];

    it('renders incoming trade signals and handles mark read', () => {
        const handleMarkRead = vi.fn();
        render(<RecipeAlertsInbox alerts={mockAlerts} onMarkRead={handleMarkRead} />);

        expect(screen.getByText('Trade Signals Inbox')).toBeInTheDocument();
        expect(screen.getByText('1 Unread')).toBeInTheDocument();
        expect(screen.getByText('BUY NVDA')).toBeInTheDocument();

        const markReadBtn = screen.getByRole('button', { name: 'Mark Read' });
        fireEvent.click(markReadBtn);
        expect(handleMarkRead).toHaveBeenCalledWith('alert-1');
    });
});

describe('WaitlistPledgeModal', () => {
    it('submits early supporter pledge', async () => {
        const handleSubmit = vi.fn().mockResolvedValue(undefined);
        const handleClose = vi.fn();

        render(<WaitlistPledgeModal isOpen={true} onClose={handleClose} onSubmit={handleSubmit} />);

        expect(screen.getByText('Early Supporter Pledge')).toBeInTheDocument();
        expect(screen.getByText(/100% Free Tier:/i)).toBeInTheDocument();

        const emailInput = screen.getByPlaceholderText('name@domain.com');
        fireEvent.change(emailInput, { target: { value: 'investor@example.com' } });

        const submitBtn = screen.getByRole('button', { name: 'Pledge Support' });
        await act(async () => {
            fireEvent.click(submitBtn);
        });

        expect(handleSubmit).toHaveBeenCalledWith('investor@example.com', 'supporter', '');
    });
});
