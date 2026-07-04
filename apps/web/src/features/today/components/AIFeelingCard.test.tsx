import type { MarketFeeling, Trade } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AIFeelingCard } from './AIFeelingCard';

type FeelingWithTime = MarketFeeling & { formattedTime?: string };
type TradeWithMeta = Trade & { portfolios: { owner_id: string }; formattedTime: string };

const makeFeeling = (overrides: Partial<FeelingWithTime> = {}): FeelingWithTime => ({
    id: 'feeling-1',
    sentiment_label: 'Bullish',
    sentiment_emoji: '🚀',
    market_direction: 'BULLISH',
    confidence_score: 75,
    why_explanation: 'Strong earnings across the board.',
    primary_concern: 'Rising interest rates',
    secondary_concern: null,
    model_used: 'gpt-4o',
    news_summary: null,
    attempts_summary: null,
    input_tokens: null,
    output_tokens: null,
    lessons_incorporated: null,
    memories_incorporated: null,
    processing_time_ms: null,
    trades_summary: null,
    created_at: '2025-06-24T09:30:00Z',
    updated_at: null,
    formattedTime: '09:30 AM',
    ...overrides,
});

const makeTrade = (signal: 'BUY' | 'SELL', id = '1'): TradeWithMeta => ({
    id,
    signal,
    ticker: 'AAPL',
    price: 150,
    quantity: 10,
    total_cost: 1500,
    portfolio_id: 'portfolio-1',
    decision_id: null,
    executed_at: '2025-06-24T09:30:00Z',
    alpaca_filled_at: null,
    alpaca_order_id: null,
    alpaca_status: null,
    alpaca_submitted_at: null,
    realized_pnl: null,
    realized_pnl_pct: null,
    reasoning: null,
    portfolios: { owner_id: 'gpt-4o' },
    formattedTime: '09:30 AM',
});

describe('AIFeelingCard', () => {
    describe('section heading', () => {
        it('always renders the section heading', () => {
            render(<AIFeelingCard marketFeeling={null} trades={[]} isSentimentStale={false} />);
            expect(screen.getByText('How is the AI Feeling?')).toBeInTheDocument();
        });
    });

    describe('with marketFeeling data', () => {
        it('renders the sentiment label', () => {
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling({ sentiment_label: 'Bearish' })}
                    trades={[]}
                    isSentimentStale={false}
                />,
            );
            expect(screen.getByText('Bearish')).toBeInTheDocument();
        });

        it('renders the direction badge', () => {
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling({ market_direction: 'BULLISH' })}
                    trades={[]}
                    isSentimentStale={false}
                />,
            );
            expect(screen.getByText('BULLISH')).toBeInTheDocument();
        });

        it('renders the why explanation', () => {
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling({ why_explanation: 'Tech sector momentum.' })}
                    trades={[]}
                    isSentimentStale={false}
                />,
            );
            expect(screen.getByText(/"Tech sector momentum\."/)).toBeInTheDocument();
        });

        it('renders the primary concern', () => {
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling({ primary_concern: 'Inflation risk' })}
                    trades={[]}
                    isSentimentStale={false}
                />,
            );
            expect(screen.getByText('Inflation risk')).toBeInTheDocument();
        });

        it('renders the last-analyzed timestamp', () => {
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling({ formattedTime: '10:15 AM' })}
                    trades={[]}
                    isSentimentStale={false}
                />,
            );
            expect(screen.getByText('Last analyzed: 10:15 AM')).toBeInTheDocument();
        });

        it('renders the model name', () => {
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling({ model_used: 'claude-opus-4' })}
                    trades={[]}
                    isSentimentStale={false}
                />,
            );
            expect(screen.getByText('claude-opus-4')).toBeInTheDocument();
        });

        it('renders stale warning when isSentimentStale is true and feeling exists', () => {
            render(
                <AIFeelingCard marketFeeling={makeFeeling()} trades={[]} isSentimentStale={true} />,
            );
            expect(screen.getByText(/STALE/)).toBeInTheDocument();
        });

        it('does not render stale warning when isSentimentStale is false', () => {
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling()}
                    trades={[]}
                    isSentimentStale={false}
                />,
            );
            expect(screen.queryByText(/STALE/)).not.toBeInTheDocument();
        });
    });

    describe('with no marketFeeling', () => {
        it('renders fallback label "Analyzing..." when marketFeeling is null', () => {
            render(<AIFeelingCard marketFeeling={null} trades={[]} isSentimentStale={false} />);
            expect(screen.getByText('Analyzing...')).toBeInTheDocument();
        });

        it('renders "Waiting for analysis..." timestamp when marketFeeling is null', () => {
            render(<AIFeelingCard marketFeeling={null} trades={[]} isSentimentStale={false} />);
            expect(screen.getByText('Waiting for analysis...')).toBeInTheDocument();
        });

        it('does not render stale warning when marketFeeling is null even if stale flag is set', () => {
            render(<AIFeelingCard marketFeeling={null} trades={[]} isSentimentStale={true} />);
            expect(screen.queryByText(/STALE/)).not.toBeInTheDocument();
        });
    });

    describe('trade split (buy/sell counts)', () => {
        it('renders buy and sell counts when trades exist', () => {
            const trades = [makeTrade('BUY', '1'), makeTrade('BUY', '2'), makeTrade('SELL', '3')];
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling()}
                    trades={trades}
                    isSentimentStale={false}
                />,
            );
            expect(screen.getByText('2')).toBeInTheDocument();
            expect(screen.getByText('1')).toBeInTheDocument();
            expect(screen.getByText('Buys')).toBeInTheDocument();
            expect(screen.getByText('Sells')).toBeInTheDocument();
        });

        it('does not render buy/sell split when there are no trades', () => {
            render(
                <AIFeelingCard
                    marketFeeling={makeFeeling()}
                    trades={[]}
                    isSentimentStale={false}
                />,
            );
            expect(screen.queryByText('Buys')).not.toBeInTheDocument();
            expect(screen.queryByText('Sells')).not.toBeInTheDocument();
        });
    });

    describe('link', () => {
        it('renders the "View full market analysis" link', () => {
            render(<AIFeelingCard marketFeeling={null} trades={[]} isSentimentStale={false} />);
            expect(screen.getByText('View full market analysis')).toBeInTheDocument();
        });
    });
});
