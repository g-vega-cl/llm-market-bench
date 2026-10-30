import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
});
