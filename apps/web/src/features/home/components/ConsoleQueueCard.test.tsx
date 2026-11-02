import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockCapture = vi.fn();
const mockCaptureException = vi.fn();

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: mockCapture,
        captureException: mockCaptureException,
    }),
}));

vi.mock('../api/fetch-agent-queue', () => ({
    MAX_QUEUE_MESSAGE_LENGTH: 500,
    submitAgentQueueQuestion: vi.fn(),
}));

import { submitAgentQueueQuestion } from '../api/fetch-agent-queue';
import { ConsoleQueueCard } from './ConsoleQueueCard';

describe('ConsoleQueueCard', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders login CTA when user is not logged in', () => {
        render(<ConsoleQueueCard user={null} pendingCount={2} />);
        expect(screen.getByText(/Audience Interactive Queue/i)).toBeInTheDocument();
        expect(screen.getByText(/2 in queue/i)).toBeInTheDocument();
        expect(screen.getByText(/Sign in to submit hypotheses/i)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /Sign In to Queue/i })).toHaveAttribute(
            'href',
            '/signup',
        );
    });

    it('renders textarea with 500 char max and submits successfully for logged in user', async () => {
        const mockSubmit = vi.mocked(submitAgentQueueQuestion);
        mockSubmit.mockResolvedValue({
            success: true,
            item: {
                id: 'q-1',
                user_id: 'usr-1',
                display_name: 'analyst',
                message: 'Testing hypothesis',
                status: 'pending',
                created_at: new Date().toISOString(),
            },
        });

        const onQueued = vi.fn();
        render(
            <ConsoleQueueCard
                user={{ id: 'usr-1', email: 'analyst@fund.com' }}
                pendingCount={0}
                onQuestionQueued={onQueued}
            />,
        );

        expect(screen.getByText(/Queue open/i)).toBeInTheDocument();
        const textarea = screen.getByPlaceholderText(/Ask a question or thesis hypothesis/i);
        expect(textarea).toHaveAttribute('maxLength', '500');

        fireEvent.change(textarea, { target: { value: 'Why did SPY reject VWAP?' } });
        expect(screen.getByText(/24\/500/i)).toBeInTheDocument();

        const submitBtn = screen.getByRole('button', { name: /Queue/i });
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(mockSubmit).toHaveBeenCalledWith({
                data: { message: 'Why did SPY reject VWAP?' },
            });
            expect(onQueued).toHaveBeenCalled();
            expect(screen.getByText(/Question queued/i)).toBeInTheDocument();
        });
    });

    it('displays latest answered question and agent thought if provided', () => {
        render(
            <ConsoleQueueCard
                user={{ id: 'usr-1', email: 'analyst@fund.com' }}
                latestAnswered={{
                    id: 'q-ans-99',
                    user_id: 'usr-2',
                    display_name: 'MacroTrader',
                    message: 'Is inflation driving the 10Y yield higher?',
                    agent_response: '10Y yield spiked 8bps following hot PPI print.',
                    status: 'answered',
                    created_at: new Date().toISOString(),
                }}
            />,
        );

        expect(screen.getByText(/Latest Answered Turn:/i)).toBeInTheDocument();
        expect(screen.getByText(/@MacroTrader/i)).toBeInTheDocument();
        expect(
            screen.getByText(/Is inflation driving the 10Y yield higher\?/i),
        ).toBeInTheDocument();
        expect(
            screen.getByText(/10Y yield spiked 8bps following hot PPI print\./i),
        ).toBeInTheDocument();
    });

    it('captures error in PostHog and displays user-friendly desk notice when response is emergency JSON fallback', () => {
        render(
            <ConsoleQueueCard
                user={{ id: 'usr-1', email: 'analyst@fund.com' }}
                latestAnswered={{
                    id: 'q-ans-crash',
                    user_id: 'usr-2',
                    display_name: 'g.vega.cl',
                    message: 'Will the market keep crashing?',
                    agent_response:
                        '{"action": "HOLD", "conviction": 50, "thought": "All LLM endpoints currently unavailable; holding neutral position.", "memories_consulted": [], "allocation_pct": 0}',
                    status: 'answered',
                    created_at: new Date().toISOString(),
                }}
            />,
        );

        expect(screen.getByText(/Latest Answered Turn:/i)).toBeInTheDocument();
        expect(screen.getByText(/@g.vega.cl/i)).toBeInTheDocument();
        expect(screen.getByText(/Will the market keep crashing\?/i)).toBeInTheDocument();

        // Assert clean desk notice is displayed
        expect(screen.getByText(/DESK NOTICE: HIGH SYSTEM VOLUME/i)).toBeInTheDocument();
        expect(
            screen.getByText(/Quantitative commentary models experienced high demand/i),
        ).toBeInTheDocument();
        // Assert raw JSON is NOT displayed
        expect(screen.queryByText(/{"action": "HOLD"/i)).not.toBeInTheDocument();

        // Assert PostHog captureException and capture were called
        expect(mockCaptureException).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'AgentLLMOutageError',
            }),
            expect.objectContaining({
                feature: 'agent_chat_queue',
                question: 'Will the market keep crashing?',
                error_type: 'llm_endpoints_unavailable',
            }),
        );
        expect(mockCapture).toHaveBeenCalledWith(
            'agent_chat_endpoint_error',
            expect.objectContaining({
                question: 'Will the market keep crashing?',
                error_type: 'llm_endpoints_unavailable',
            }),
        );
    });
});
