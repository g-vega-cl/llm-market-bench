import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { BacktestDayStep } from '../types';
import { BacktestSessionTraceBlock } from './BacktestSessionTraceBlock';

const sampleStep: BacktestDayStep = {
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
};

describe('BacktestSessionTraceBlock', () => {
    it('renders nothing before window dates exist', () => {
        const { container } = render(
            <BacktestSessionTraceBlock
                windowDates={[]}
                activeDay={null}
                activeIndex={-1}
                selectedStep={undefined}
                isCurrentRunning={false}
                onSelectDay={vi.fn()}
            />,
        );
        expect(container).toBeEmptyDOMElement();
    });

    it('supports Prev/Next session stepping and timeline anchor link', () => {
        const onSelectDay = vi.fn();
        render(
            <BacktestSessionTraceBlock
                windowDates={['2026-08-03 09:30 ET', '2026-08-03 12:30 ET']}
                activeDay="2026-08-03 09:30 ET"
                activeIndex={0}
                selectedStep={sampleStep}
                isCurrentRunning={false}
                onSelectDay={onSelectDay}
            />,
        );

        expect(screen.getByRole('button', { name: /Prev/i })).toBeDisabled();
        const nextBtn = screen.getByRole('button', { name: /Next/i });
        expect(nextBtn).toBeEnabled();
        fireEvent.click(nextBtn);
        expect(onSelectDay).toHaveBeenCalledWith('2026-08-03 12:30 ET');

        expect(screen.getByRole('link', { name: /Timeline/i })).toHaveAttribute(
            'href',
            '#simulation-timeline',
        );
        expect(
            screen.getByText(
                /Hold decision: evaluated 1 PIT tool call across 1 reasoning round and stayed in cash/i,
            ),
        ).toBeInTheDocument();
    });
});
