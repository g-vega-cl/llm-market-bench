import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ExperimentDetails } from './ExperimentDetails';

const baseExperiment: PromptExperiment = {
    id: 'exp-1',
    variant_tag: 'v1.1',
    prompt_name: 'CORE_ANALYSIS_SYSTEM_PROMPT',
    prompt_content: '=== MUTABLE STRATEGY SECTION ===\nTest strategy\n=== CORE ANALYSIS PROMPT ===',
    week_start: '2026-07-20',
    week_end: '2026-07-26',
    metrics: { score: 12.5, excess_return: 3.2, max_drawdown: 1.1 },
    status: 'active',
    experiment_type: 'incremental',
    parent_tag: 'v1.0',
    change_description: 'Added volatility analysis tools',
    research_output: {
        selected_tools: [
            'get_portfolio_ledger',
            'get_todays_news_menu',
            'fetch_newsletter_content',
            'get_market_feeling',
            'search_past_memories',
            'get_stock_quote',
            'get_price_history',
            'get_position_pnl',
            'get_volatility_metrics',
            'get_sector_alternatives',
            'search_related_tickers',
            'run_stock_screener',
            'find_uncorrelated_assets',
            'get_key_metrics',
            'get_market_health_barometer',
            'get_earnings_history',
            'search_prediction_markets',
            'get_prediction_market_odds',
            'audit_financial_valuation',
            'web_search',
            'get_global_macro_context',
            'get_volatility_index_details',
            'get_verifier_rejections',
        ],
    },
    is_backtest: false,
    created_at: '2026-07-20T00:00:00Z',
    track_id: 'track_default',
};

describe('ExperimentDetails Toolbox Configuration', () => {
    it('renders 23 / 26 Tools Enabled badge when 23 tools are selected from 26 canonical tools', () => {
        render(<ExperimentDetails experiment={baseExperiment} />);

        expect(screen.getByText('Weekly Toolbox Configuration')).toBeInTheDocument();
        expect(screen.getByText('23 / 26 Tools Enabled')).toBeInTheDocument();
        expect(screen.getByText('get_global_macro_context')).toBeInTheDocument();
        expect(screen.getByText('get_volatility_index_details')).toBeInTheDocument();
        expect(screen.getByText('get_verifier_rejections')).toBeInTheDocument();
    });

    it('dynamically absorbs unknown tools to guarantee selected count never exceeds total', () => {
        const customExperiment: PromptExperiment = {
            ...baseExperiment,
            research_output: {
                selected_tools: ['get_portfolio_ledger', 'future_hypothetical_quantum_tool'],
            },
        };

        render(<ExperimentDetails experiment={customExperiment} />);

        // 26 canonical tools + 1 unknown extra tool = 27 total
        expect(screen.getByText('2 / 27 Tools Enabled')).toBeInTheDocument();
        expect(screen.getByText('future_hypothetical_quantum_tool')).toBeInTheDocument();
    });
});
