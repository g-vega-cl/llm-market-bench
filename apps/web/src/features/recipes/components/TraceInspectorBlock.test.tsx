import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { TraceInspectorBlock } from './TraceInspectorBlock';

describe('TraceInspectorBlock', () => {
    it('renders hydrated prompt, multi-round reasoning, tool results, and forced synthesis badge', () => {
        render(
            <TraceInspectorBlock
                prompt="You are a semiconductor momentum trader."
                trace={{
                    forced_final_synthesis: true,
                    rounds: [
                        {
                            round: 1,
                            reasoning: 'First check NVDA quote and volume.',
                            assistant_text: 'Checking NVDA now.',
                            tool_calls: [
                                {
                                    name: 'get_stock_quote',
                                    args: { ticker: 'NVDA' },
                                    result: '{"price": 210.5}',
                                },
                            ],
                        },
                        {
                            round: 2,
                            reasoning: 'Confirming breakout.',
                            assistant_text: '[{"action": "BUY", "ticker": "NVDA"}]',
                            tool_calls: [],
                        },
                    ],
                }}
                fullOutput='[{"action": "BUY", "ticker": "NVDA"}]'
            />,
        );

        expect(screen.getByText('You are a semiconductor momentum trader.')).toBeInTheDocument();
        expect(screen.getByText('LLM Execution Trace (2 Rounds)')).toBeInTheDocument();
        expect(screen.getByText('Forced Final Synthesis')).toBeInTheDocument();
        expect(screen.getByText('First check NVDA quote and volume.')).toBeInTheDocument();
        expect(screen.getByText('Checking NVDA now.')).toBeInTheDocument();
        expect(screen.getByText('get_stock_quote({"ticker":"NVDA"})')).toBeInTheDocument();
        expect(screen.getByText('{"price": 210.5}')).toBeInTheDocument();
        expect(screen.getByText('[{"action": "BUY", "ticker": "NVDA"}]')).toBeInTheDocument();
    });

    it('falls back to flat toolCalls strings when legacy trace has no rounds', () => {
        render(
            <TraceInspectorBlock
                toolCalls={['get_market_news({"limit": 5})']}
                outputExcerpt="HOLD today"
            />,
        );

        expect(screen.getByText('Tools Called')).toBeInTheDocument();
        expect(screen.getByText('get_market_news({"limit": 5})')).toBeInTheDocument();
        expect(screen.getByText('HOLD today')).toBeInTheDocument();
    });
});
