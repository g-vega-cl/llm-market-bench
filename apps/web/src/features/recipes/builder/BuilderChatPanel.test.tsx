import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
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

beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: true,
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    });

    if (typeof globalThis.ResizeObserver === 'undefined') {
        globalThis.ResizeObserver = class ResizeObserver {
            observe() {}
            unobserve() {}
            disconnect() {}
        };
    }
});

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

describe('BuilderChatPanel (SceneStage, Starter Chips, 3-Step Flow & Alignment Card)', () => {
    it('renders on SceneStage with GardenBackdrop, starter chips, 3-step stepper, and sr-only h1', () => {
        const { container } = renderWithQuery(
            <BuilderChatPanel userId="user-1" initialAtmosphere="dusk" />,
        );

        const stage = container.querySelector('section[data-slot="scene-stage"]');
        expect(stage).toBeInTheDocument();
        expect(stage).toHaveAttribute('data-atmosphere', 'dusk');
        expect(screen.getByTestId('garden-backdrop')).toBeInTheDocument();

        const starterChips = screen.getByTestId('builder-starter-chips');
        expect(starterChips).toBeInTheDocument();

        const stepper = screen.getByTestId('builder-stepper');
        expect(stepper.querySelector('[data-step-number="1"]')).toHaveAttribute(
            'data-step-state',
            'active',
        );

        const pageHeading = screen.getByRole('heading', {
            level: 1,
            name: /build a trading bot from one sentence/i,
        });
        expect(pageHeading).toHaveClass('sr-only');
        expect(screen.getByTestId('builder-stage-card')).toHaveClass('voxel-card', 'scene-scrim');

        // Clicking a starter chip fills the strategy textarea.
        fireEvent.click(screen.getByRole('button', { name: 'AI Capex Chips' }));
        expect(screen.getByLabelText('Describe your trading bot')).toHaveValue(
            'Buy profitable semiconductor leaders on AI data-center capex news with RSI under 65 and positive MACD.',
        );
    });

    it('places the primary Continue to Alignment CTA below the textarea and supports Ctrl/Cmd+Enter submit', async () => {
        renderWithQuery(<BuilderChatPanel userId="user-1" />);

        const submitButton = screen.getByRole('button', { name: /continue to alignment/i });
        const textarea = screen.getByLabelText('Describe your trading bot');
        expect(textarea.tagName).toBe('TEXTAREA');
        expect(textarea).toHaveAttribute('maxLength', '2000');
        expect(submitButton).toHaveClass('voxel-btn--hero');

        // Textarea sits above the primary CTA in DOM order.
        expect(
            textarea.compareDocumentPosition(submitButton) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();

        fireEvent.change(textarea, { target: { value: 'Buy chipmakers on AI capex news' } });
        fireEvent.keyDown(textarea, { key: 'Enter' });
        expect(enqueueCompileFn).not.toHaveBeenCalled();

        fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });
        expect(enqueueCompileFn).toHaveBeenCalledTimes(1);
        expect(await screen.findByTestId('builder-compile-pipeline')).toBeInTheDocument();
    });

    it('walks through the 3-5 MCQ alignment round and compiles into CompiledBotWorkspace', async () => {
        vi.mocked(fetchCompileJobFn)
            .mockResolvedValueOnce({
                id: 'job-compile-1',
                status: 'completed',
                progress_pct: 100,
                result_json: {
                    content: JSON.stringify({
                        status: 'align',
                        intro: 'Align on 3 quick choices.',
                        questions: [
                            {
                                id: 'q1',
                                question: 'Ticker focus?',
                                options: ['NVDA/AMD', 'Broad semis'],
                            },
                            {
                                id: 'q2',
                                question: 'Entry filter?',
                                options: ['RSI < 65', 'MACD > 0'],
                            },
                            {
                                id: 'q3',
                                question: 'Exit rule?',
                                options: ['Thesis break', 'RSI > 80'],
                            },
                        ],
                    }),
                },
                error_message: null,
            } as never)
            .mockResolvedValueOnce({
                id: 'job-compile-2',
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

        vi.mocked(enqueueCompileFn)
            .mockResolvedValueOnce({ jobId: 'job-compile-1' } as never)
            .mockResolvedValueOnce({ jobId: 'job-compile-2' } as never);

        renderWithQuery(<BuilderChatPanel userId="user-1" />);

        fireEvent.change(screen.getByLabelText('Describe your trading bot'), {
            target: { value: 'Buy chipmakers on AI capex news' },
        });
        fireEvent.click(screen.getByRole('button', { name: /continue to alignment/i }));

        const alignCard = await screen.findByTestId('builder-alignment-card');
        expect(alignCard).toBeInTheDocument();
        expect(
            screen.getByTestId('builder-stepper').querySelector('[data-step-number="2"]'),
        ).toHaveAttribute('data-step-state', 'active');

        const buildFinalBtn = screen.getByRole('button', { name: /build final bot/i });
        expect(buildFinalBtn).toBeDisabled();

        fireEvent.click(screen.getByRole('button', { name: 'NVDA/AMD' }));
        fireEvent.click(screen.getByRole('button', { name: 'RSI < 65' }));
        fireEvent.click(screen.getByRole('button', { name: 'Thesis break' }));

        expect(buildFinalBtn).toBeEnabled();
        fireEvent.click(buildFinalBtn);

        const heroCard = await screen.findByTestId('compiled-bot-hero-card');
        expect(heroCard).toHaveClass('voxel-card');
        expect(heroCard).not.toHaveClass('scene-scrim');

        await waitFor(() =>
            expect(screen.getByRole('button', { name: /describe a different bot/i })).toBeEnabled(),
        );
        fireEvent.click(screen.getByRole('button', { name: /describe a different bot/i }));
        expect(screen.getByTestId('builder-stage-card')).toBeInTheDocument();
    });

    it('keeps BuilderAlignmentCard mounted at Step 2 on failure and preserves custom text matching an option', async () => {
        vi.mocked(enqueueCompileFn)
            .mockResolvedValueOnce({ jobId: 'job-align-err-1' } as never)
            .mockRejectedValueOnce(new Error('Worker busy') as never);
        vi.mocked(fetchCompileJobFn).mockResolvedValueOnce({
            id: 'job-align-err-1',
            status: 'completed',
            progress_pct: 100,
            result_json: {
                content: JSON.stringify({
                    status: 'align',
                    questions: [
                        { id: 'q1', question: 'Ticker focus?', options: ['NVDA', 'AMD'] },
                        { id: 'q2', question: 'Entry filter?', options: ['RSI < 65', 'MACD > 0'] },
                        { id: 'q3', question: 'Exit rule?', options: ['Thesis break', 'RSI > 80'] },
                    ],
                }),
            },
            error_message: null,
        } as never);

        renderWithQuery(<BuilderChatPanel userId="user-1" />);

        fireEvent.change(screen.getByLabelText('Describe your trading bot'), {
            target: { value: 'Buy chipmakers on AI capex news' },
        });
        fireEvent.click(screen.getByRole('button', { name: /continue to alignment/i }));

        await screen.findByTestId('builder-alignment-card');
        const customInput = screen.getByLabelText('Custom answer for question 1');
        fireEvent.change(customInput, { target: { value: 'NVDA' } });
        expect(customInput).toHaveValue('NVDA');

        fireEvent.click(screen.getByRole('button', { name: 'RSI < 65' }));
        fireEvent.click(screen.getByRole('button', { name: 'Thesis break' }));
        fireEvent.click(screen.getByRole('button', { name: /build final bot/i }));

        expect(await screen.findByRole('alert')).toHaveTextContent('Worker busy');
        expect(screen.getByTestId('builder-alignment-card')).toBeInTheDocument();
        expect(
            screen.getByTestId('builder-stepper').querySelector('[data-step-number="2"]'),
        ).toHaveAttribute('data-step-state', 'active');
        expect(screen.getByLabelText('Custom answer for question 1')).toHaveValue('NVDA');
    });

    it('opens CompiledBotWorkspace with a live-execution warning instead of blocking on offline limitations', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValueOnce({
            id: 'job-compile-1',
            status: 'completed',
            progress_pct: 100,
            result_json: {
                content: JSON.stringify({
                    status: 'declined',
                    reason: 'Benchify cannot access congressional trading disclosures or super PAC donation data in its offline toolset.',
                    closest:
                        'A long-only stock bot that buys large-cap stocks using recent news and technicals.',
                }),
            },
            error_message: null,
        } as never);

        renderWithQuery(<BuilderChatPanel userId="user-1" />);

        fireEvent.change(screen.getByLabelText('Describe your trading bot'), {
            target: { value: 'Follow congressional trades and super PAC donations' },
        });
        fireEvent.click(screen.getByRole('button', { name: /continue to alignment/i }));

        expect(await screen.findByTestId('compiled-bot-hero-card')).toBeInTheDocument();
        expect(screen.getByTestId('compiled-bot-live-warning')).toHaveTextContent(
            /congressional trading disclosures/i,
        );
        expect(screen.getByTestId('builder-status')).toHaveTextContent(/CLOSEST WORKING TEMPLATE/i);
        expect(screen.getByRole('button', { name: /Enable Live \(30m\)/i })).toBeEnabled();
        expect(screen.getByRole('button', { name: /▶ Backtest \(Random 2W\)/i })).toBeEnabled();
    });
});
