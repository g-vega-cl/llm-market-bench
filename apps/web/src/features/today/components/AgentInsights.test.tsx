import { render, screen } from '@testing-library/react';
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
        render(<AgentInsights memories={[createLessonMemory('gpt-5.4-nano')]} />);
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
        render(<AgentInsights memories={[createLessonMemory('gpt-5.4-nano')]} />);
        expect(screen.getByText('Lesson Learned')).toBeInTheDocument();
    });

    it('still renders Post-Analysis label', () => {
        render(<AgentInsights memories={[createLessonMemory('gpt-5.4-nano')]} />);
        expect(screen.getByText(/Post-Analysis/i)).toBeInTheDocument();
    });

    it('renders lesson content', () => {
        render(<AgentInsights memories={[createLessonMemory('gpt-5.4-nano')]} />);
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
                participating_agents: ['gpt-5.4-nano', 'gemini-3.1-flash-lite'],
                tickers: ['NVDA'],
            },
        };
        render(<AgentInsights memories={[consensusMemory]} />);
        expect(screen.getByText('Agreed:')).toBeInTheDocument();
        expect(screen.getByText('OpenAI, Gemini')).toBeInTheDocument();
    });
});
