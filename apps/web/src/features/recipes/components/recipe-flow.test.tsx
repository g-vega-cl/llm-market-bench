import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import {
    type BacktestResultData,
    CURATED_TOOLS,
    type RecipeAlert,
    type StrategyStage,
} from '../types';
import { PromptVisualizer } from './PromptVisualizer';
import { RecipeAlertsInbox } from './RecipeAlertsInbox';
import { RecipeBacktestResults } from './RecipeBacktestResults';
import { StageBuilder } from './StageBuilder';
import { WaitlistPledgeModal } from './WaitlistPledgeModal';

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        className?: string;
    }) => {
        let href = to;
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                href = href.replace(`$${k}`, v);
            }
        }
        return (
            <a href={href} className={className}>
                {children}
            </a>
        );
    },
}));

function ControlledStageHarness({ initialStage }: { initialStage: StrategyStage }) {
    const [stage, setStage] = useState<StrategyStage>(initialStage);
    return (
        <div>
            <StageBuilder stage={stage} onChange={setStage} />
            <PromptVisualizer
                stage={stage}
                previewState={{ status: 'template' }}
                onPreviewLiveData={vi.fn()}
            />
        </div>
    );
}

describe('StageBuilder & PromptVisualizer', () => {
    it('renders all 4 block types and updates PromptVisualizer live', () => {
        render(<ControlledStageHarness initialStage={STARTER_RECIPES[0].stages[0]} />);

        expect(screen.getByText('PROMPT BLOCK')).toBeInTheDocument();
        expect(screen.getByText('NEWS BLOCK')).toBeInTheDocument();
        expect(screen.getByText('MEMORIES BLOCK')).toBeInTheDocument();
        expect(screen.getByText('TECHNICALS BLOCK')).toBeInTheDocument();
        expect(screen.getByText('OUTPUT_FORMAT BLOCK')).toBeInTheDocument();
        expect(screen.getByText(/Prompt Visualizer/i)).toBeInTheDocument();
        expect(screen.getByText(/P\/E < 45/)).toBeInTheDocument();
    });

    it('preserves input focus across multi-character typing (fixes 1-char typing bug)', () => {
        render(<ControlledStageHarness initialStage={STARTER_RECIPES[0].stages[0]} />);

        const targetInputs = screen.getAllByLabelText('Target Value') as HTMLInputElement[];
        const firstTarget = targetInputs[0];
        firstTarget.focus();
        expect(document.activeElement).toBe(firstTarget);

        fireEvent.change(firstTarget, { target: { value: '1' } });
        expect(document.activeElement).toBe(firstTarget);

        fireEvent.change(firstTarget, { target: { value: '12' } });
        expect(document.activeElement).toBe(firstTarget);

        fireEvent.change(firstTarget, { target: { value: '125' } });
        expect(document.activeElement).toBe(firstTarget);
        expect(firstTarget.value).toBe('125');
        expect(screen.getByText(/P\/E < 125/)).toBeInTheDocument();
    });

    it('keeps prompt block pinned first (non-deletable) and toggles tools', () => {
        render(<ControlledStageHarness initialStage={STARTER_RECIPES[0].stages[0]} />);

        expect(screen.getByRole('button', { name: '+ Prompt' })).toBeDisabled();
        expect(screen.getByText('PINNED FIRST')).toBeInTheDocument();
        expect(screen.getAllByText('PROMPT BLOCK').length).toBe(1);

        const initialCount = STARTER_RECIPES[0].stages[0].selected_tools.length;
        expect(screen.getByText(`${initialCount} / ${CURATED_TOOLS.length}`)).toBeInTheDocument();

        const techCheckbox = screen.getByRole('checkbox', { name: 'Technical Indicators' });
        fireEvent.click(techCheckbox);
        expect(
            screen.getByText(`${initialCount - 1} / ${CURATED_TOOLS.length}`),
        ).toBeInTheDocument();

        fireEvent.click(techCheckbox);
        expect(screen.getByText(`${initialCount} / ${CURATED_TOOLS.length}`)).toBeInTheDocument();
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
});

describe('RecipeAlertsInbox & WaitlistPledgeModal', () => {
    it('renders alerts inbox and marks alert as read', () => {
        const mockAlerts: RecipeAlert[] = [
            {
                id: 'a-1',
                user_id: 'u-1',
                recipe_id: 'r-1',
                recipe_name: 'NVDA Momentum',
                ticker: 'NVDA',
                action: 'BUY',
                entry_price: 120.5,
                target_price: 125.0,
                stop_loss: 118.0,
                timeframe: '5m',
                reason: 'Price > VWAP and RSI > 55',
                is_read: false,
                created_at: new Date().toISOString(),
            },
        ];
        const onMarkRead = vi.fn();

        render(<RecipeAlertsInbox alerts={mockAlerts} onClose={vi.fn()} onMarkRead={onMarkRead} />);

        expect(screen.getByText(/BUY\s+NVDA/)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'NVDA Momentum' })).toHaveAttribute(
            'href',
            '/recipes/live/r-1',
        );
        const markBtn = screen.getByRole('button', { name: 'Mark Read' });
        fireEvent.click(markBtn);
        expect(onMarkRead).toHaveBeenCalledWith('a-1');
    });

    it('renders WaitlistPledgeModal when open', () => {
        render(<WaitlistPledgeModal isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} />);
        expect(screen.getByText(/Your Email Address/i)).toBeInTheDocument();
    });
});
