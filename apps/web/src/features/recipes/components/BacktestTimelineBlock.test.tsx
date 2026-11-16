import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import type { BacktestResultData } from '../types';
import { BacktestSessionTraceBlock } from './BacktestSessionTraceBlock';
import { BacktestTimelineBlock, resolveBacktestTimelineSelection } from './BacktestTimelineBlock';

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

function ConnectedTimelineAndTrace({
    status,
    results,
    queuePosition,
}: {
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
    results: BacktestResultData | null;
    queuePosition?: number | null;
}) {
    const [selectedDay, setSelectedDay] = useState<string | null>(null);
    const selection = resolveBacktestTimelineSelection(status, results, selectedDay);
    return (
        <>
            <BacktestTimelineBlock
                queuePosition={queuePosition}
                selection={selection}
                onSelectDay={setSelectedDay}
            />
            <BacktestSessionTraceBlock
                windowDates={selection.windowDates}
                activeDay={selection.activeDay}
                activeIndex={selection.activeIndex}
                selectedStep={selection.selectedStep}
                isCurrentRunning={selection.isCurrentRunning}
                onSelectDay={setSelectedDay}
            />
        </>
    );
}

describe('BacktestTimelineBlock', () => {
    it('renders queue waiting trough before window dates exist and hides trace block', () => {
        render(<ConnectedTimelineAndTrace status="pending" results={null} />);
        expect(
            screen.getByText(/Waiting for recipe worker to pick a 2-week historical window/i),
        ).toBeInTheDocument();
        expect(screen.queryByTestId('day-inspector-trough')).not.toBeInTheDocument();
    });

    it('renders settled, running, and queued session tiles with compact bar and trace controls', () => {
        render(<ConnectedTimelineAndTrace status="processing" results={partialResults} />);

        expect(screen.getByText('1 / 3 Sessions Settled')).toBeInTheDocument();
        expect(screen.getAllByText('S1 • 2026-08-03 09:30 ET').length).toBeGreaterThanOrEqual(2);
        expect(screen.getAllByText('EXIT AMD').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('-$12.50')).toBeInTheDocument();
        expect(screen.getAllByText('RUNNING').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('QUEUED')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /Jump to Trace/i })).toHaveAttribute(
            'href',
            '#session-trace',
        );

        fireEvent.click(screen.getByRole('button', { name: /2026-08-03 12:30 ET/ }));
        expect(
            screen.getAllByText('Running LLM evaluation for this session...').length,
        ).toBeGreaterThanOrEqual(2);

        fireEvent.click(screen.getByRole('button', { name: /2026-08-03 09:30 ET/ }));
        expect(screen.getAllByText(/1 open/).length).toBeGreaterThanOrEqual(2);
        expect(screen.getByText('get_stock_quote({"ticker":"AMD"})')).toBeInTheDocument();
        expect(screen.getByText('[{"action": "EXIT", "ticker": "AMD"}]')).toBeInTheDocument();

        const nextBtn = screen.getByRole('button', { name: /Next/i });
        const prevBtn = screen.getByRole('button', { name: /Prev/i });
        expect(prevBtn).toBeDisabled();
        expect(nextBtn).toBeEnabled();
        fireEvent.click(nextBtn);
        expect(
            screen.getAllByText('Running LLM evaluation for this session...').length,
        ).toBeGreaterThanOrEqual(2);
        expect(screen.getByRole('link', { name: /Timeline/i })).toHaveAttribute(
            'href',
            '#simulation-timeline',
        );
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

        render(<ConnectedTimelineAndTrace status="completed" results={tracedResults} />);

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
            <ConnectedTimelineAndTrace status="pending" results={null} queuePosition={3} />,
        );
        expect(screen.getByText(/Queued \(#3 in line\)/i)).toBeInTheDocument();

        rerender(
            <ConnectedTimelineAndTrace
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
