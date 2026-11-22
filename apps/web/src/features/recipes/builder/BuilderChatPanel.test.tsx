import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { CEDAR_WORLD_ID } from '../../home/backdrop/voxel-world';
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
            matches: false,
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

describe('BuilderChatPanel (Cedar Sanctuary SceneStage & Voxel Pipeline)', () => {
    it('renders on SceneStage with reactive motion role, SSR atmosphere parity, and open-sky header', () => {
        const { container } = renderWithQuery(
            <BuilderChatPanel userId="user-1" initialAtmosphere="after-hours" />,
        );

        const stage = container.querySelector('section[data-slot="scene-stage"]');
        expect(stage).not.toBeNull();
        expect(stage).toHaveAttribute('data-stage-variant', 'hero');
        expect(stage).toHaveAttribute('data-motion-role', 'reactive');
        expect(stage).toHaveAttribute('data-atmosphere', 'after-hours');
        expect(stage?.className).toContain('scene-atmosphere-after-hours');

        const canvas = screen.getByTestId('garden-backdrop');
        expect(canvas).toHaveAttribute('data-world', CEDAR_WORLD_ID);
        expect(canvas).toHaveAttribute('data-atmosphere', 'after-hours');

        expect(
            screen.getByRole('heading', { name: /build your trading bot/i }),
        ).toBeInTheDocument();
        expect(screen.getByTestId('builder-stage-card')).toHaveClass('scene-scrim', 'voxel-card');
        expect(screen.getByTestId('atmosphere-switcher')).toHaveTextContent('Sky: After-Hours');
    });

    it('populates the prompt input when clicking a starter-idea chip without auto-submitting', () => {
        renderWithQuery(<BuilderChatPanel userId={null} initialAtmosphere="dusk" />);

        const chips = screen.getByTestId('builder-starter-chips');
        expect(chips).toBeInTheDocument();

        const firstChip = chips.querySelector('button');
        expect(firstChip).not.toBeNull();
        fireEvent.click(firstChip as HTMLButtonElement);

        const input = screen.getByLabelText('Describe your trading bot') as HTMLInputElement;
        expect(input.value.trim().length).toBeGreaterThan(10);
        expect(enqueueCompileFn).not.toHaveBeenCalled();
        expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('reflects real queued vs compiling pipeline states honestly and uses recessed troughs for chat messages', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValueOnce({
            id: 'job-compile-1',
            status: 'pending',
            progress_pct: 0,
            result_json: null,
            error_message: null,
        } as never);

        renderWithQuery(<BuilderChatPanel userId="user-1" initialAtmosphere="daylight" />);

        const input = screen.getByLabelText('Describe your trading bot');
        fireEvent.change(input, { target: { value: 'Buy chipmakers on AI capex news' } });
        fireEvent.click(screen.getByRole('button', { name: /build my bot/i }));

        const pipeline = await screen.findByTestId('builder-compile-pipeline');
        expect(pipeline).toBeInTheDocument();
        expect(pipeline).toHaveTextContent(/1\. Queue/i);
        expect(pipeline).toHaveTextContent(/2\. Model/i);
        expect(pipeline).toHaveTextContent(/3\. Validate/i);
        expect(pipeline.querySelectorAll('[data-step-state="active"]')).toHaveLength(1);

        // Conversation rows inside .scene-scrim .voxel-card must use recessed .voxel-trough, zero nested .voxel-card
        const stageCard = screen.getByTestId('builder-stage-card');
        expect(stageCard.querySelectorAll('.voxel-card')).toHaveLength(0);
        expect(stageCard.querySelector('[data-testid="builder-message-row"]')).toHaveClass(
            'voxel-trough',
        );
    });

    it('preserves user atmosphere and paused HUD state across Step 1 -> Step 2 and Start Over', async () => {
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

        renderWithQuery(<BuilderChatPanel userId="user-1" initialAtmosphere="dawn" />);

        // Cycle sky dawn -> daylight and pause motion in Step 1
        fireEvent.click(screen.getByTestId('atmosphere-switcher'));
        expect(screen.getByTestId('atmosphere-switcher')).toHaveTextContent('Sky: Daylight');
        fireEvent.click(screen.getByRole('button', { name: /pause motion/i }));
        expect(screen.getByRole('button', { name: /play motion/i })).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText('Describe your trading bot'), {
            target: { value: 'Buy chipmakers on AI capex news' },
        });
        fireEvent.click(screen.getByRole('button', { name: /build my bot/i }));

        const heroCard = await screen.findByTestId('compiled-bot-hero-card');
        expect(heroCard).toHaveClass('scene-scrim', 'voxel-card');
        expect(screen.getByTestId('garden-backdrop')).toHaveAttribute(
            'data-atmosphere',
            'daylight',
        );
        expect(screen.getByRole('button', { name: /play motion/i })).toBeInTheDocument();

        // Cycle sky daylight -> dusk in Step 2, then click Describe a different bot
        fireEvent.click(screen.getByTestId('atmosphere-switcher'));
        expect(screen.getByTestId('atmosphere-switcher')).toHaveTextContent('Sky: Dusk');
        fireEvent.click(screen.getByRole('button', { name: /describe a different bot/i }));

        expect(screen.getByTestId('builder-stage-card')).toBeInTheDocument();
        expect(screen.getByTestId('garden-backdrop')).toHaveAttribute('data-atmosphere', 'dusk');
    });
});
