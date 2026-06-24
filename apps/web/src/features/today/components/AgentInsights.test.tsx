import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MODELS } from '~/config/models';
import { AgentInsights } from './AgentInsights';

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
});
