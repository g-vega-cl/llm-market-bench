import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { BacktestResultData } from '../types';
import { BacktestTimelineBlock } from './BacktestTimelineBlock';

const partialResults: BacktestResultData = {
    window_dates: ['2026-08-03 09:30 ET', '2026-08-03 12:30 ET', '2026-08-03 15:30 ET'],
    days_completed: 1,
    total_days: 3,
    current_day: '2026-08-03 12:30 ET',
    total_return_pct_midpoint: 0,
    total_return_pct_net: 0,
    total_trades: 0,
    win_rate_pct: 0,
    max_drawdown_pct: 0,
    equity_curve: [{ time: '2026-08-03 09:30 ET', equity: 10000 }],
    trades: [],
    day_steps: [
        {
            day: '2026-08-03 09:30 ET',
            day_index: 0,
            status: 'completed',
            signals: [{ action: 'EXIT', ticker: 'AMD' }],
            tool_calls: ['get_stock_quote({"ticker":"AMD"})'],
            output_excerpt: '[{"action": "EXIT", "ticker": "AMD"}]',
            day_pnl_net: -12.5,
            trades_executed: 1,
            trades_skipped: 0,
            open_positions_count: 1,
        },
    ],
};

describe('BacktestTimelineBlock', () => {
    it('renders queue waiting trough before window dates exist', () => {
        render(<BacktestTimelineBlock status="pending" results={null} />);
        expect(
            screen.getByText(/Waiting for recipe worker to pick a 2-week historical window/i),
        ).toBeInTheDocument();
    });

    it('renders settled, running, and queued session tiles and inspects clicked session in-flow', () => {
        render(<BacktestTimelineBlock status="processing" results={partialResults} />);

        expect(screen.getByText('1 / 3 Sessions Settled')).toBeInTheDocument();
        expect(screen.getByText('S1 • 2026-08-03 09:30 ET')).toBeInTheDocument();
        expect(screen.getByText('EXIT AMD')).toBeInTheDocument();
        expect(screen.getByText('-$12.50')).toBeInTheDocument();
        expect(screen.getByText('RUNNING')).toBeInTheDocument();
        expect(screen.getByText('QUEUED')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /2026-08-03 12:30 ET/ }));
        expect(screen.getByText('Running LLM evaluation for this session...')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /2026-08-03 09:30 ET/ }));
        expect(screen.getByText(/1 open/)).toBeInTheDocument();
        expect(screen.getByText('get_stock_quote({"ticker":"AMD"})')).toBeInTheDocument();
        expect(screen.getByText('[{"action": "EXIT", "ticker": "AMD"}]')).toBeInTheDocument();
    });

    it('renders hydrated prompt, round-by-round reasoning, tool results, and full unclipped output', () => {
        const baseStep = partialResults.day_steps?.[0];
        if (!baseStep) throw new Error('Expected base day step');
        const tracedResults: BacktestResultData = {
            ...partialResults,
            day_steps: [
                {
                    ...baseStep,
                    prompt: 'Hydrated Stage Prompt for 2026-08-03',
                    full_output:
                        'Full reasoning summary beyond 600 chars: [{"action": "EXIT", "ticker": "AMD"}]',
                    trace: {
                        forced_final_synthesis: true,
                        rounds: [
                            {
                                round: 1,
                                reasoning: 'Need to check AMD quote before exiting.',
                                assistant_text: '',
                                tool_calls: [
                                    {
                                        name: 'get_stock_quote',
                                        args: { ticker: 'AMD' },
                                        result: 'Ticker: AMD | Price: $148.20',
                                    },
                                ],
                            },
                        ],
                    },
                },
            ],
        };

        render(<BacktestTimelineBlock status="completed" results={tracedResults} />);

        expect(screen.getByText('Hydrated Stage Prompt for 2026-08-03')).toBeInTheDocument();
        expect(screen.getByText('Need to check AMD quote before exiting.')).toBeInTheDocument();
        expect(screen.getByText('Ticker: AMD | Price: $148.20')).toBeInTheDocument();
        expect(
            screen.getByText(
                'Full reasoning summary beyond 600 chars: [{"action": "EXIT", "ticker": "AMD"}]',
            ),
        ).toBeInTheDocument();
    });

    it('renders queue position waiting message and clear hold decision summary', () => {
        const { rerender } = render(
            <BacktestTimelineBlock status="pending" results={null} queuePosition={3} />,
        );
        expect(screen.getByText(/Queued \(#3 in line\)/i)).toBeInTheDocument();

        rerender(
            <BacktestTimelineBlock
                status="completed"
                results={{
                    ...partialResults,
                    day_steps: [
                        {
                            day: '2026-08-03 09:30 ET',
                            day_index: 0,
                            status: 'completed',
                            signals: [],
                            tool_calls: ['get_stock_quote({"ticker":"NVDA"})'],
                            output_excerpt: '[]',
                            full_output: '[]',
                            day_pnl_net: 0,
                            trades_executed: 0,
                            trades_skipped: 0,
                            trace: {
                                forced_final_synthesis: false,
                                rounds: [
                                    {
                                        round: 1,
                                        reasoning: 'Wait for catalyst.',
                                        assistant_text: '[]',
                                        tool_calls: [],
                                    },
                                ],
                            },
                        },
                    ],
                }}
            />,
        );

        expect(
            screen.getByText(
                /Hold decision: evaluated 1 PIT tool call across 1 reasoning round and stayed in cash/i,
            ),
        ).toBeInTheDocument();
    });
});
