import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ChatPage } from './ChatPage';

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        Link: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
            <a {...props}>{children}</a>
        ),
    };
});

vi.mock('./chat-types', () => ({
    ALLOWED_CHAT_EMAILS: ['g.vega.cl@gmail.com'],
    SUGGESTED_RESEARCH_PROMPTS: [
        'Should I invest in NVO based on current memories and trades?',
        'What is the current market feeling and today’s morning briefing?',
    ],
}));

vi.mock('./chat-server', () => ({
    sendChatMessageFn: vi.fn(),
    distillChatMemoryFn: vi.fn(),
    saveChatMemoryFn: vi.fn(),
}));

import { distillChatMemoryFn, saveChatMemoryFn, sendChatMessageFn } from './chat-server';

describe('ChatPage Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
    });

    it('renders gated private beta banner when user is not authorized', () => {
        render(<ChatPage user={null} />);
        expect(screen.getAllByText(/Investment Chat Gateway/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/Private Beta/i)).toBeInTheDocument();
        expect(screen.getByText(/Sign In to Access/i)).toBeInTheDocument();
    });

    it('renders gated private beta banner when user is signed in with unauthorized email', () => {
        render(<ChatPage user={{ email: 'outsider@example.com' }} />);
        expect(screen.getByText(/Signed in as outsider@example.com/i)).toBeInTheDocument();
        expect(screen.getByText(/Sign In to Access/i)).toBeInTheDocument();
    });

    it('renders interactive terminal for authorized users with suggestions', () => {
        render(<ChatPage user={{ email: 'g.vega.cl@gmail.com' }} />);
        expect(screen.getByText(/Benchify AI Gateway/i)).toBeInTheDocument();
        expect(screen.getByText(/Live DB Connected/i)).toBeInTheDocument();
        expect(
            screen.getByText(/Should I invest in NVO based on current memories and trades?/i),
        ).toBeInTheDocument();
    });

    it('handles clicking suggested prompt chip and displays tool traces', async () => {
        (sendChatMessageFn as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
            role: 'assistant',
            content: 'NVO shows strong GLP-1 momentum and past positive agent trades.',
            tool_traces: [
                {
                    tool_name: 'search_memories_and_theses',
                    summary: 'Retrieved 3 memories for NVO',
                },
            ],
        });

        render(<ChatPage user={{ email: 'g.vega.cl@gmail.com' }} />);

        const chip = screen.getByText(
            /Should I invest in NVO based on current memories and trades?/i,
        );
        fireEvent.click(chip);

        await waitFor(() => {
            expect(
                screen.getByText(
                    /NVO shows strong GLP-1 momentum and past positive agent trades./i,
                ),
            ).toBeInTheDocument();
        });

        // Check tool trace accordion
        const traceToggle = screen.getByText(/1 tool call executed/i);
        expect(traceToggle).toBeInTheDocument();

        fireEvent.click(traceToggle);
        expect(screen.getByText('Retrieved 3 memories for NVO')).toBeInTheDocument();
    });

    it('clears conversation history when Clear button is clicked', async () => {
        render(<ChatPage user={{ email: 'g.vega.cl@gmail.com' }} />);

        const clearBtn = screen.getByRole('button', { name: /clear/i });
        fireEvent.click(clearBtn);

        expect(screen.getByText(/Welcome to the/i)).toBeInTheDocument();
    });

    it('renders next best question chips and dispatches message when clicked', async () => {
        (sendChatMessageFn as unknown as ReturnType<typeof vi.fn>)
            .mockResolvedValueOnce({
                role: 'assistant',
                content: 'Analysis for NVDA completed.',
                suggested_questions: [
                    'Compare NVDA against AMD in recent trades',
                    'Check NVDA causal memories for volatility risks',
                ],
            })
            .mockResolvedValueOnce({
                role: 'assistant',
                content: 'NVDA vs AMD comparison details.',
            });

        render(<ChatPage user={{ email: 'g.vega.cl@gmail.com' }} />);

        const chip = screen.getByText(
            /Should I invest in NVO based on current memories and trades?/i,
        );
        fireEvent.click(chip);

        await waitFor(() => {
            expect(screen.getByText('Next best questions:')).toBeInTheDocument();
            expect(
                screen.getByText('Compare NVDA against AMD in recent trades'),
            ).toBeInTheDocument();
            expect(
                screen.getByText('Check NVDA causal memories for volatility risks'),
            ).toBeInTheDocument();
        });

        const followUpChip = screen.getByText('Compare NVDA against AMD in recent trades');
        fireEvent.click(followUpChip);

        await waitFor(() => {
            expect(sendChatMessageFn).toHaveBeenCalledTimes(2);
            expect(screen.getByText('NVDA vs AMD comparison details.')).toBeInTheDocument();
        });
    });

    it('promotes assistant message to private memory when Promote to Memory is clicked', async () => {
        (sendChatMessageFn as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
            role: 'assistant',
            content: 'NVO shows strong GLP-1 revenue momentum.',
        });

        (distillChatMemoryFn as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
            ticker: 'NVO',
            thesis: 'NVO GLP-1 revenue momentum is robust.',
            tags: ['GLP-1', 'pharma'],
            importance_score: 8,
        });

        (saveChatMemoryFn as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
            id: 'saved-mem-123',
            user_id: 'user-1',
            ticker: 'NVO',
            thesis: 'NVO GLP-1 revenue momentum is robust.',
            tags: ['GLP-1', 'pharma'],
            importance_score: 8,
            created_at: '2026-09-04T12:00:00Z',
        });

        render(<ChatPage user={{ email: 'g.vega.cl@gmail.com' }} />);

        const chip = screen.getByText(
            /Should I invest in NVO based on current memories and trades?/i,
        );
        fireEvent.click(chip);

        await waitFor(() => {
            expect(screen.getByText('Promote to Memory')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Promote to Memory'));

        await waitFor(() => {
            expect(screen.getByText(/Promote Insight to Private Memory/i)).toBeInTheDocument();
            expect(
                screen.getByDisplayValue('NVO GLP-1 revenue momentum is robust.'),
            ).toBeInTheDocument();
        });

        const saveButton = screen.getByRole('button', { name: /Save to My Theses/i });
        fireEvent.click(saveButton);

        await waitFor(() => {
            expect(saveChatMemoryFn).toHaveBeenCalled();
            expect(screen.getByText(/✓ Saved to My Theses/i)).toBeInTheDocument();
        });
    });
});
