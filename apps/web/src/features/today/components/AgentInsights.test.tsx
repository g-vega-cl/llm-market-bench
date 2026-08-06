import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MODELS } from '~/config/models';
import { AgentInsights } from './AgentInsights';

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        Link: ({
            children,
            to,
            params,
            ...props
        }: {
            children: React.ReactNode;
            to: string;
            params?: { memoryId?: string };
            [key: string]: unknown;
        }) => {
            const href = to.replace('$memoryId', params?.memoryId || '');
            return (
                <a href={href} {...props}>
                    {children}
                </a>
            );
        },
    };
});

describe('AgentInsights', () => {
    const createLessonMemory = (modelName?: string, id = '1') => ({
        id,
        content: 'Test lesson learned',
        created_at: '2025-04-01T12:00:00Z',
        memory_type: 'LESSON_LEARNED',
        status: 'ACTIVE',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        importance_score: null,
        target_date: null,
        metadata: modelName ? { model_name: modelName } : {},
    });

    const createConsensusMemory = (id = '1') => ({
        id,
        content: 'Test consensus event',
        created_at: '2025-04-01T12:00:00Z',
        memory_type: 'MARKET_EVENT',
        status: 'ACTIVE',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        importance_score: 8,
        target_date: null,
        metadata: {
            participating_agents: ['gemini-2-pro'],
            tickers: ['NVDA'],
        },
    });

    const createIncentiveMemory = (id = '2') => ({
        id,
        content: 'Test incentive event',
        created_at: '2025-04-01T12:00:00Z',
        memory_type: 'GOVERNMENT_INCENTIVE',
        status: 'ACTIVE',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        importance_score: null,
        target_date: null,
        metadata: {
            budget: '$10B',
        },
    });

    it('renders agent name text for known Gemini model', () => {
        render(<AgentInsights memories={[createLessonMemory(MODELS.GEMINI)]} />);
        expect(screen.getByText('Gemini')).toBeInTheDocument();
    });

    it('renders agent name text for known OpenAI model', () => {
        render(<AgentInsights memories={[createLessonMemory(MODELS.OPENAI)]} />);
        expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    it('renders agent name text for known Claude model', () => {
        render(<AgentInsights memories={[createLessonMemory('claude-haiku-4-5')]} />);
        expect(screen.getByText('Claude')).toBeInTheDocument();
    });

    it('renders agent name text for known DeepSeek model', () => {
        render(<AgentInsights memories={[createLessonMemory('deepseek-v4-pro')]} />);
        expect(screen.getByText('DeepSeek')).toBeInTheDocument();
    });

    it('renders agent name text for Contrarian agent', () => {
        render(<AgentInsights memories={[createLessonMemory('contrarian_agent')]} />);
        expect(screen.getByText('Contrarian')).toBeInTheDocument();
    });

    it('does not render agent indicator when model_name is missing', () => {
        render(<AgentInsights memories={[createLessonMemory()]} />);
        expect(screen.queryByText('OpenAI')).not.toBeInTheDocument();
        expect(screen.queryByText('Gemini')).not.toBeInTheDocument();
        expect(screen.queryByText('Claude')).not.toBeInTheDocument();
        expect(screen.queryByText('Unknown')).not.toBeInTheDocument();
    });

    it('does not render agent indicator for unknown model', () => {
        render(<AgentInsights memories={[createLessonMemory('some-unknown-model')]} />);
        // Unknown model → getAgentInfo returns 'Unknown' → component hides indicator
        expect(screen.queryByText('Unknown')).not.toBeInTheDocument();
    });

    it('still renders Lesson Learned badge', () => {
        render(<AgentInsights memories={[createLessonMemory(MODELS.OPENAI)]} />);
        expect(screen.getByText('Lesson Learned')).toBeInTheDocument();
    });

    it('still renders Post-Analysis label', () => {
        render(<AgentInsights memories={[createLessonMemory(MODELS.OPENAI)]} />);
        expect(screen.getByText(/Post-Analysis/i)).toBeInTheDocument();
    });

    it('renders lesson content', () => {
        render(<AgentInsights memories={[createLessonMemory(MODELS.OPENAI)]} />);
        expect(screen.getByText(/Test lesson learned/i)).toBeInTheDocument();
    });

    it('renders empty-state heading when no relevant memories exist', () => {
        render(<AgentInsights memories={[]} />);
        expect(screen.getByText('AI Cognitive Synthesis')).toBeInTheDocument();
    });

    it('renders empty-state message when no relevant memories exist', () => {
        render(<AgentInsights memories={[]} />);
        expect(screen.getByText('No insights synthesized yet today')).toBeInTheDocument();
    });

    it('renders empty-state when memories exist but none are relevant types', () => {
        const irrelevantMemory = {
            ...createLessonMemory(),
            memory_type: 'SOME_OTHER_TYPE',
        };
        render(<AgentInsights memories={[irrelevantMemory]} />);
        expect(screen.getByText('No insights synthesized yet today')).toBeInTheDocument();
    });

    it('links Consensus memory card to its event chain page', () => {
        render(<AgentInsights memories={[createConsensusMemory('consensus-123')]} />);
        const link = screen.getByRole('link');
        expect(link).toHaveAttribute('href', '/memories/chain/consensus-123');
        expect(screen.getByText(/View event chain/i)).toBeInTheDocument();
    });

    it('links Government Incentive memory card to its event chain page', () => {
        render(<AgentInsights memories={[createIncentiveMemory('incentive-123')]} />);
        const link = screen.getByRole('link');
        expect(link).toHaveAttribute('href', '/memories/chain/incentive-123');
        expect(screen.getByText(/View event chain/i)).toBeInTheDocument();
    });

    it('links Lesson Learned memory card to its event chain page', () => {
        render(<AgentInsights memories={[createLessonMemory(undefined, 'lesson-123')]} />);
        const link = screen.getByRole('link');
        expect(link).toHaveAttribute('href', '/memories/chain/lesson-123');
        expect(screen.getByText(/View event chain/i)).toBeInTheDocument();
    });

    it('renders agreed models as an inline text list for consensus memory', () => {
        const consensusMemory = {
            ...createConsensusMemory('consensus-123'),
            metadata: {
                participating_agents: [MODELS.OPENAI, 'gemini-3.5-flash-lite'],
                tickers: ['NVDA'],
            },
        };
        render(<AgentInsights memories={[consensusMemory]} />);
        expect(screen.getByText('Agreed:')).toBeInTheDocument();
        expect(screen.getByText('OpenAI, Gemini')).toBeInTheDocument();
    });

    it('renders total insights badge and view toggle buttons when memories are present', () => {
        render(
            <AgentInsights memories={[createConsensusMemory('1'), createIncentiveMemory('2')]} />,
        );
        expect(screen.getByText(/2 Insights/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /List/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Cards/i })).toBeInTheDocument();
    });

    it('toggles view mode when clicking List and Cards buttons', () => {
        render(
            <AgentInsights
                memories={[createConsensusMemory('1'), createLessonMemory(MODELS.GEMINI, '2')]}
            />,
        );

        const cardsBtn = screen.getByRole('button', { name: /Cards/i });
        const listBtn = screen.getByRole('button', { name: /List/i });

        // By default list mode is selected
        expect(listBtn).toHaveAttribute('data-active', 'true');
        expect(cardsBtn).toHaveAttribute('data-active', 'false');

        // Click Cards toggle
        fireEvent.click(cardsBtn);
        expect(cardsBtn).toHaveAttribute('data-active', 'true');
        expect(listBtn).toHaveAttribute('data-active', 'false');
    });

    // --------------- Pagination tests ---------------

    const make6Memories = () => [
        createConsensusMemory('c1'),
        createConsensusMemory('c2'),
        createConsensusMemory('c3'),
        createIncentiveMemory('i1'),
        createIncentiveMemory('i2'),
        createLessonMemory(undefined, 'l1'),
    ];

    it('renders at most 5 items on the first page when more than 5 memories exist', () => {
        render(<AgentInsights memories={make6Memories()} />);
        // Each card renders exactly one "View event chain →" link — use that as a
        // reliable per-item sentinel that is present in both list and cards view.
        const links = screen.getAllByText(/View event chain/i);
        expect(links).toHaveLength(5);
    });

    it('shows a "Next" button when there are more than 5 memories', () => {
        render(<AgentInsights memories={make6Memories()} />);
        expect(screen.getByRole('button', { name: /Next/i })).toBeInTheDocument();
    });

    it('hides the "Prev" button on the first page', () => {
        render(<AgentInsights memories={make6Memories()} />);
        expect(screen.queryByRole('button', { name: /Prev/i })).not.toBeInTheDocument();
    });

    it('shows a page indicator (e.g. "Page 1 of 2") when pagination is active', () => {
        render(<AgentInsights memories={make6Memories()} />);
        expect(screen.getByText(/Page 1 of 2/i)).toBeInTheDocument();
    });

    it('navigating to page 2 shows the remaining item and hides "Next"', () => {
        render(<AgentInsights memories={make6Memories()} />);
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));
        const links = screen.getAllByText(/View event chain/i);
        expect(links).toHaveLength(1);
        expect(screen.queryByRole('button', { name: /Next/i })).not.toBeInTheDocument();
        expect(screen.getByText(/Page 2 of 2/i)).toBeInTheDocument();
    });

    it('navigating back to page 1 via "Prev" restores 5 items', () => {
        render(<AgentInsights memories={make6Memories()} />);
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));
        fireEvent.click(screen.getByRole('button', { name: /Prev/i }));
        const links = screen.getAllByText(/View event chain/i);
        expect(links).toHaveLength(5);
        expect(screen.queryByRole('button', { name: /Prev/i })).not.toBeInTheDocument();
    });

    it('does not render pagination controls when 5 or fewer memories exist', () => {
        render(
            <AgentInsights
                memories={[
                    createConsensusMemory('c1'),
                    createConsensusMemory('c2'),
                    createIncentiveMemory('i1'),
                    createLessonMemory(undefined, 'l1'),
                    createLessonMemory(undefined, 'l2'),
                ]}
            />,
        );
        expect(screen.queryByRole('button', { name: /Next/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Prev/i })).not.toBeInTheDocument();
        expect(screen.queryByText(/Page \d of \d/i)).not.toBeInTheDocument();
    });

    it('resets to page 1 when view mode is toggled', () => {
        render(<AgentInsights memories={make6Memories()} />);
        // Advance to page 2
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));
        expect(screen.getByText(/Page 2 of 2/i)).toBeInTheDocument();
        // Switch view mode → should reset page
        fireEvent.click(screen.getByRole('button', { name: /Cards/i }));
        expect(screen.getByText(/Page 1 of 2/i)).toBeInTheDocument();
    });
});
