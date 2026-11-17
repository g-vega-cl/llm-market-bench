import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { RecipeJobRecord } from '../types';
import { LiveRunsBlock } from './LiveRunsBlock';

describe('LiveRunsBlock', () => {
    const sampleRuns: RecipeJobRecord[] = [
        {
            id: 'run-newer-111',
            mode: 'live_turn',
            status: 'completed',
            progress_pct: 100,
            error_message: null,
            created_at: '2026-11-15T15:30:00Z',
            result_json: {
                mode: 'live_turn',
                as_of_utc: '2026-11-15T15:30:00Z',
                slot_label: '2026-11-15 10:30 ET',
                final_output: '[{"action": "BUY", "ticker": "MSFT"}]',
                signals: [{ action: 'BUY', ticker: 'MSFT' }],
                stages: [
                    {
                        stage_id: 's1',
                        prompt: 'Prompt newer',
                        output: '[{"action": "BUY", "ticker": "MSFT"}]',
                        tool_calls: [],
                        trace: {
                            forced_final_synthesis: false,
                            rounds: [
                                {
                                    round: 1,
                                    reasoning: 'Newer reasoning',
                                    assistant_text: '',
                                    tool_calls: [],
                                },
                            ],
                        },
                    },
                ],
            },
        },
        {
            id: 'run-older-222',
            mode: 'live_turn',
            status: 'completed',
            progress_pct: 100,
            error_message: null,
            created_at: '2026-11-14T15:30:00Z',
            result_json: {
                mode: 'live_turn',
                as_of_utc: '2026-11-14T15:30:00Z',
                slot_label: '2026-11-14 10:30 ET',
                final_output: 'HOLD',
                signals: [],
                stages: [
                    {
                        stage_id: 's1',
                        prompt: 'Prompt older',
                        output: 'HOLD',
                        tool_calls: [],
                        trace: {
                            forced_final_synthesis: false,
                            rounds: [
                                {
                                    round: 1,
                                    reasoning: 'Older reasoning',
                                    assistant_text: '',
                                    tool_calls: [],
                                },
                            ],
                        },
                    },
                ],
            },
        },
    ];

    it('renders nothing when neither portfolio nor live runs exist', () => {
        const { container } = render(
            <LiveRunsBlock portfolio={null} recentLiveRuns={[]} latestInlineRun={null} />,
        );
        expect(container).toBeEmptyDOMElement();
    });

    it('renders portfolio and switches between recent persisted live runs', () => {
        render(
            <LiveRunsBlock
                portfolio={{
                    cash: 8000,
                    total_equity: 10100,
                    open_positions: [],
                    trades: [],
                }}
                recentLiveRuns={sampleRuns}
                latestInlineRun={null}
            />,
        );

        expect(screen.getByText('Live Paper Portfolio')).toBeInTheDocument();
        expect(screen.getByText('Prompt newer')).toBeInTheDocument();
        expect(screen.getByText('Newer reasoning')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: '2026-11-14 15:30' }));
        expect(screen.getByText('Prompt older')).toBeInTheDocument();
        expect(screen.getByText('Older reasoning')).toBeInTheDocument();
    });

    it('lets user inspect an older run and return to Latest Turn inline trace', () => {
        const inlineRun = {
            mode: 'live_turn' as const,
            as_of_utc: '2026-11-15T18:00:00Z',
            slot_label: '2026-11-15 13:00 ET',
            final_output: '[{"action": "BUY", "ticker": "AVGO"}]',
            signals: [{ action: 'BUY', ticker: 'AVGO' }],
            stages: [
                {
                    stage_id: 's1',
                    prompt: 'Inline prompt',
                    output: '[{"action": "BUY", "ticker": "AVGO"}]',
                    tool_calls: [],
                },
            ],
        };

        render(
            <LiveRunsBlock
                portfolio={{ cash: 8000, total_equity: 8000, open_positions: [], trades: [] }}
                recentLiveRuns={sampleRuns}
                latestInlineRun={inlineRun}
            />,
        );

        expect(screen.getByText('Inline prompt')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: '2026-11-14 15:30' }));
        expect(screen.getByText('Prompt older')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Latest Turn' }));
        expect(screen.getByText('Inline prompt')).toBeInTheDocument();
    });
});
