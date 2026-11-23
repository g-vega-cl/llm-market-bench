import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { BuilderChatPanel } from './BuilderChatPanel';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        className,
        ...rest
    }: {
        children: React.ReactNode;
        to: string;
        className?: string;
    }) => (
        <a href={to} className={className} {...rest}>
            {children}
        </a>
    ),
    useRouter: () => ({ navigate: mockNavigate }),
    useNavigate: () => mockNavigate,
}));

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({ capture: vi.fn() }),
}));

vi.mock('./compile-queue', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./compile-queue')>()),
    enqueueCompileFn: vi.fn(),
    fetchCompileJobFn: vi.fn(),
    cancelCompileFn: vi.fn(),
}));

import { enqueueCompileFn, fetchCompileJobFn } from './compile-queue';

function renderWithQuery(ui: React.ReactElement) {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockResolvedValue(undefined);
    vi.mocked(enqueueCompileFn).mockResolvedValue({ jobId: 'job-compile-1' } as never);
    vi.mocked(fetchCompileJobFn).mockResolvedValue({
        id: 'job-compile-1',
        status: 'processing',
        progress_pct: 50,
        result_json: null,
        error_message: null,
    } as never);
});

describe('BuilderChatPanel (GlobalBackground, Expansible Textarea & Voxel Pipeline)', () => {
    it('renders transparently without diorama/starter chips and shows 16-question personality link', () => {
        const { container } = renderWithQuery(<BuilderChatPanel userId="user-1" />);

        expect(container.querySelector('section[data-slot="scene-stage"]')).toBeNull();
        expect(screen.queryByTestId('garden-backdrop')).toBeNull();
        expect(screen.queryByTestId('builder-starter-chips')).toBeNull();

        const pageHeading = screen.getByRole('heading', {
            level: 1,
            name: /build a trading bot from one sentence/i,
        });
        expect(pageHeading).toHaveClass('sr-only');
        expect(screen.getByTestId('builder-stage-card')).toHaveClass('voxel-card');
        expect(screen.getByTestId('builder-stage-card')).not.toHaveClass('scene-scrim');

        const personalityLink = screen.getByRole('link', {
            name: /16-question personality test/i,
        });
        expect(personalityLink).toHaveAttribute('href', '/personality');
    });

    it('places the Build My Bot button above an expansible textarea and supports Ctrl/Cmd+Enter submit', async () => {
        renderWithQuery(<BuilderChatPanel userId="user-1" />);

        const submitButton = screen.getByRole('button', { name: /build my bot/i });
        const textarea = screen.getByLabelText('Describe your trading bot');
        expect(textarea.tagName).toBe('TEXTAREA');
        expect(textarea).toHaveAttribute('maxLength', '2000');
        const describedBy = textarea.getAttribute('aria-describedby');
        expect(describedBy).toBeTruthy();
        expect(document.getElementById(describedBy as string)).toHaveTextContent(
            /0 \/ 2000 · Ctrl\/⌘\+Enter to submit/,
        );

        // Button appears above the textarea in DOM order.
        expect(
            submitButton.compareDocumentPosition(textarea) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();

        // Plain Enter does not submit; Ctrl+Enter submits when non-empty.
        fireEvent.change(textarea, { target: { value: 'Buy chipmakers on AI capex news' } });
        fireEvent.keyDown(textarea, { key: 'Enter' });
        expect(enqueueCompileFn).not.toHaveBeenCalled();

        fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });
        expect(enqueueCompileFn).toHaveBeenCalledTimes(1);
        expect(await screen.findByTestId('builder-compile-pipeline')).toBeInTheDocument();
    });

    it('reflects real queued vs compiling pipeline states honestly and uses recessed troughs for chat messages', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValueOnce({
            id: 'job-compile-1',
            status: 'pending',
            progress_pct: 0,
            result_json: null,
            error_message: null,
        } as never);

        renderWithQuery(<BuilderChatPanel userId="user-1" />);

        const textarea = screen.getByLabelText('Describe your trading bot');
        fireEvent.change(textarea, { target: { value: 'Buy chipmakers on AI capex news' } });
        fireEvent.click(screen.getByRole('button', { name: /build my bot/i }));

        const pipeline = await screen.findByTestId('builder-compile-pipeline');
        expect(pipeline).toBeInTheDocument();
        expect(pipeline).toHaveTextContent(/1\. Queue/i);
        expect(pipeline).toHaveTextContent(/2\. Model/i);
        expect(pipeline).toHaveTextContent(/3\. Validate/i);
        expect(pipeline.querySelectorAll('[data-step-state="active"]')).toHaveLength(1);

        // Conversation rows inside .voxel-card must use recessed .voxel-trough, zero nested .voxel-card
        const stageCard = screen.getByTestId('builder-stage-card');
        expect(stageCard.querySelectorAll('.voxel-card')).toHaveLength(0);
        expect(stageCard.querySelector('[data-testid="builder-message-row"]')).toHaveClass(
            'voxel-trough',
        );
    });

    it('transitions to CompiledBotWorkspace on compile completion and returns cleanly on Start Over', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue({
            id: 'job-compile-1',
            status: 'completed',
            progress_pct: 100,
            result_json: {
                content: JSON.stringify({
                    status: 'ok',
                    strategy: STARTER_RECIPES[0],
                    summary: 'Compiled chip momentum bot.',
                }),
            },
            error_message: null,
        } as never);

        renderWithQuery(<BuilderChatPanel userId="user-1" />);

        fireEvent.change(screen.getByLabelText('Describe your trading bot'), {
            target: { value: 'Buy chipmakers on AI capex news' },
        });
        fireEvent.click(screen.getByRole('button', { name: /build my bot/i }));

        const heroCard = await screen.findByTestId('compiled-bot-hero-card');
        expect(heroCard).toHaveClass('voxel-card');
        expect(heroCard).not.toHaveClass('scene-scrim');

        fireEvent.click(screen.getByRole('button', { name: /describe a different bot/i }));
        expect(screen.getByTestId('builder-stage-card')).toBeInTheDocument();
    });
});
