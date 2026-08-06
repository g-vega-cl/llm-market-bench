import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ChatWidget } from './ChatWidget';

vi.mock('./chat-server', () => ({
    ALLOWED_CHAT_EMAILS: ['g.vega.cl@gmail.com'],
    sendChatMessageFn: vi.fn(),
}));

import { sendChatMessageFn } from './chat-server';

describe('ChatWidget Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should return null when user is null or not in allowed list', () => {
        const { container: container1 } = render(<ChatWidget user={null} />);
        expect(container1.firstChild).toBeNull();

        const { container: container2 } = render(
            <ChatWidget user={{ email: 'unauthorized@example.com' }} />,
        );
        expect(container2.firstChild).toBeNull();
    });

    it('should render trigger button for g.vega.cl@gmail.com', () => {
        render(<ChatWidget user={{ email: 'g.vega.cl@gmail.com' }} />);
        const button = screen.getByRole('button', { name: /chat/i });
        expect(button).toBeInTheDocument();
    });

    it('should toggle chat drawer when clicking trigger button', () => {
        render(<ChatWidget user={{ email: 'g.vega.cl@gmail.com' }} />);
        const trigger = screen.getByRole('button', { name: /chat/i });

        // Drawer closed initially
        expect(screen.queryByText(/Benchify AI/i)).not.toBeInTheDocument();

        // Open drawer
        fireEvent.click(trigger);
        expect(screen.getByRole('heading', { name: /Benchify AI/i })).toBeInTheDocument();

        // Close drawer
        const closeBtn = screen.getByRole('button', { name: /close chat/i });
        fireEvent.click(closeBtn);
        expect(screen.queryByRole('heading', { name: /Benchify AI/i })).not.toBeInTheDocument();
    });

    it('should submit prompt and render assistant response', async () => {
        (sendChatMessageFn as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
            role: 'assistant',
            content: 'Consensus sentiment is currently 72% bullish.',
        });

        render(<ChatWidget user={{ email: 'g.vega.cl@gmail.com' }} />);

        // Open drawer
        fireEvent.click(screen.getByRole('button', { name: /chat/i }));

        // Type input
        const input = screen.getByPlaceholderText(/type a message/i);
        fireEvent.change(input, { target: { value: 'What is the market consensus?' } });

        // Submit form
        const sendBtn = screen.getByRole('button', { name: /send/i });
        fireEvent.click(sendBtn);

        // Verify user message appears immediately
        expect(screen.getByText('What is the market consensus?')).toBeInTheDocument();

        // Wait for assistant response
        await waitFor(() => {
            expect(
                screen.getByText('Consensus sentiment is currently 72% bullish.'),
            ).toBeInTheDocument();
        });
    });
});
