import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { getMemoryCategory, MemoriesList, type Memory } from './MemoriesList';

// Mock the Link component from TanStack Router
vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        Link: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
            <a {...props}>{children}</a>
        ),
    };
});

const mockMemories: Memory[] = [
    {
        id: '1',
        content: 'Consensus on rate hike',
        created_at: new Date().toISOString(),
        metadata: {
            type: 'consensus_event',
            impact: 'BEARISH',
            scenario_analysis:
                'Scenario A: Rates go up -> Trading Plan (How to Profit): Buy bank stocks. Scenario B: Rates go down -> Trading Plan (How to Profit): Buy tech stocks.',
        },
        status: 'ACTIVE',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        memory_type: 'MARKET_EVENT',
        importance_score: null,
        target_date: null,
    },
    {
        id: '2',
        content: 'Decision to buy TSLA',
        created_at: new Date().toISOString(),
        metadata: { type: 'decision_reasoning', ticker: 'TSLA', signal: 'BUY' },
        parent_id: '1',
        relationship_type: 'UPDATE',
        status: 'ACTIVE',
        relevance_score: null,
        memory_type: null,
        importance_score: null,
        target_date: null,
    },
    {
        id: '3',
        content: 'Post-mortem on AAPL',
        created_at: new Date().toISOString(),
        metadata: { type: 'post_mortem', ticker: 'AAPL', is_regret: true },
        status: 'RESOLVED',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        memory_type: null,
        importance_score: null,
        target_date: null,
    },
];

describe('MemoriesList', () => {
    it('renders all memories passed to it', () => {
        const onFilterChange = vi.fn();
        render(
            <MemoriesList memories={mockMemories} filter="all" onFilterChange={onFilterChange} />,
        );
        expect(screen.getByText('Consensus on rate hike')).toBeInTheDocument();
        expect(screen.getByText('Decision to buy TSLA')).toBeInTheDocument();
        expect(screen.getByText('Post-mortem on AAPL')).toBeInTheDocument();
    });

    it('filter buttons use DS Button component and omit Decisions and Lessons', () => {
        const onFilterChange = vi.fn();
        render(
            <MemoriesList memories={mockMemories} filter="all" onFilterChange={onFilterChange} />,
        );

        // Only the active, populated filter pills (All, Events, Calendar Events, Post-Mortems, Principles)
        const filterButtons = screen.getAllByRole('button');
        const dsButtons = filterButtons.filter((btn) =>
            ['All', 'Events', 'Calendar Events', 'Post-Mortems', 'Principles'].includes(
                btn.textContent || '',
            ),
        );
        expect(dsButtons.length).toBe(5);

        // Decisions and Lessons must be completely gone
        expect(screen.queryByText('Decisions')).not.toBeInTheDocument();
        expect(screen.queryByText('Lessons')).not.toBeInTheDocument();

        for (const btn of dsButtons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });

    it('triggers onFilterChange when a filter button is clicked', () => {
        const onFilterChange = vi.fn();
        render(
            <MemoriesList memories={mockMemories} filter="all" onFilterChange={onFilterChange} />,
        );

        const eventsButton = screen.getByText('Events');
        fireEvent.click(eventsButton);

        expect(onFilterChange).toHaveBeenCalledWith('consensus_event');
    });

    it('displays metadata badges correctly', () => {
        const onFilterChange = vi.fn();
        render(
            <MemoriesList memories={mockMemories} filter="all" onFilterChange={onFilterChange} />,
        );
        expect(screen.getByText('BEARISH')).toBeInTheDocument();
        expect(screen.getByText('$TSLA')).toBeInTheDocument();
        expect(screen.getByText('Regret')).toBeInTheDocument();
    });

    it('shows empty state when no memories are passed', () => {
        const onFilterChange = vi.fn();
        render(<MemoriesList memories={[]} filter="all" onFilterChange={onFilterChange} />);
        expect(screen.getByText('No memories found in this category')).toBeInTheDocument();
    });

    it('expands scenario analysis when button is clicked', () => {
        const onFilterChange = vi.fn();
        render(
            <MemoriesList memories={mockMemories} filter="all" onFilterChange={onFilterChange} />,
        );

        const analysisButton = screen.getByText('Show Analysis');
        expect(screen.queryByText('Scenario Analysis')).not.toBeInTheDocument();

        fireEvent.click(analysisButton);

        expect(screen.getByText('Scenario Analysis')).toBeInTheDocument();
        expect(screen.getByText('Buy bank stocks.')).toBeInTheDocument();
    });

    it('shows event chain link for memories with parent', () => {
        const onFilterChange = vi.fn();
        render(
            <MemoriesList memories={mockMemories} filter="all" onFilterChange={onFilterChange} />,
        );

        // Memory 2 has a parent
        expect(screen.getByText('View event chain →')).toBeInTheDocument();
    });

    describe('Memory Category Classification', () => {
        it('classifies consensus_event and calendar_event correctly', () => {
            const m1: Memory = {
                id: '1',
                content: 'Market event content',
                created_at: '',
                metadata: { type: 'consensus_event' },
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: null,
                target_date: null,
            };
            expect(getMemoryCategory(m1)).toBe('consensus_event');

            const m2: Memory = {
                id: '2',
                content: 'Calendar event',
                created_at: '',
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'CALENDAR_EVENT',
                importance_score: null,
                target_date: null,
            };
            expect(getMemoryCategory(m2)).toBe('calendar_event');
        });

        it('classifies academic principles correctly', () => {
            const m: Memory = {
                id: '1',
                content: 'Empirical pricing rule',
                created_at: '',
                metadata: { source_type: 'academic_paper' },
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'LESSON_LEARNED',
                importance_score: null,
                target_date: null,
            };
            expect(getMemoryCategory(m)).toBe('academic_paper');
        });

        it('classifies post_mortems and lessons correctly', () => {
            const mPost: Memory = {
                id: '1',
                content: 'Post-mortem details',
                created_at: '',
                metadata: { analysis_window: '5' },
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'LESSON_LEARNED',
                importance_score: null,
                target_date: null,
            };
            expect(getMemoryCategory(mPost)).toBe('post_mortem');

            const mLesson: Memory = {
                id: '2',
                content: 'General trading lesson learned',
                created_at: '',
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'LESSON_LEARNED',
                importance_score: null,
                target_date: null,
            };
            expect(getMemoryCategory(mLesson)).toBe('lesson_learned');
        });
    });
});
