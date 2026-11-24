import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { RecipeJobRecord } from '../types';
import { LiveRunTracesCard } from './LiveRunTracesCard';

function job(overrides: Partial<RecipeJobRecord> & { id: string }): RecipeJobRecord {
    return {
        recipe_id: 'rec-1',
        mode: 'live_turn',
        status: 'completed',
        progress_pct: 100,
        result_json: {
            mode: 'live_turn',
            as_of_utc: '2026-04-06T09:30:00Z',
            stages: [
                {
                    stage_id: 's1',
                    prompt: 'Analyze NVDA.',
                    output: 'BUY NVDA',
                    tool_calls: [],
                    trace: { rounds: [], forced_final_synthesis: false },
                },
            ],
            final_output: '[]',
            signals: [{ action: 'BUY', ticker: 'NVDA' }],
        },
        error_message: null,
        created_at: '2026-04-06T09:32:00Z',
        ...overrides,
    } as RecipeJobRecord;
}

describe('LiveRunTracesCard', () => {
    it('renders nothing without runs', () => {
        const { container } = render(
            <LiveRunTracesCard runs={[]} pageIndex={0} onOlder={vi.fn()} onNewer={vi.fn()} />,
        );

        expect(container).toBeEmptyDOMElement();
    });

    it('renders the paged run trace and the run stamp', () => {
        render(
            <LiveRunTracesCard
                runs={[job({ id: 'a' })]}
                pageIndex={0}
                onOlder={vi.fn()}
                onNewer={vi.fn()}
            />,
        );

        expect(screen.getByText(/Live Run Traces/i)).toBeInTheDocument();
        expect(screen.getByText('Apr 6 • 5:32 AM ET')).toBeInTheDocument();
        expect(screen.getByText(/LLM Call/i)).toBeInTheDocument();
        expect(screen.getByText(/Analyze NVDA\./i)).toBeInTheDocument();
        // A single run has no pages to move between.
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    it('names a queued run instead of claiming a missing trace will arrive', () => {
        render(
            <LiveRunTracesCard
                runs={[
                    job({
                        id: 'a',
                        status: 'pending',
                        result_json: null,
                        created_at: '2026-04-06T15:32:00Z',
                    }),
                    job({ id: 'b' }),
                ]}
                pageIndex={0}
                onOlder={vi.fn()}
                onNewer={vi.fn()}
            />,
        );

        expect(screen.getByText('queued — no trace output yet')).toBeInTheDocument();
        expect(screen.getByRole('status')).toHaveTextContent('1 of 2');
    });

    it('reports a failed run as terminal, with its error, and pages older', () => {
        const onOlder = vi.fn();
        render(
            <LiveRunTracesCard
                runs={[
                    job({
                        id: 'a',
                        status: 'failed',
                        result_json: null,
                        error_message: 'LLM timeout',
                        created_at: '2026-04-06T15:32:00Z',
                    }),
                    job({ id: 'b' }),
                ]}
                pageIndex={0}
                onOlder={onOlder}
                onNewer={vi.fn()}
            />,
        );

        expect(screen.getByText('failed — no trace output')).toBeInTheDocument();
        expect(screen.queryByText(/no trace output yet/i)).not.toBeInTheDocument();
        expect(screen.getByText('LLM timeout')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Older' }));
        expect(onOlder).toHaveBeenCalledTimes(1);
    });
});
