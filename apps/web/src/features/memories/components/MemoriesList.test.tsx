import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoriesList, type Memory } from './MemoriesList';

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
    it('renders all memories by default', () => {
        render(<MemoriesList memories={mockMemories} />);
        expect(screen.getByText('Consensus on rate hike')).toBeInTheDocument();
        expect(screen.getByText('Decision to buy TSLA')).toBeInTheDocument();
        expect(screen.getByText('Post-mortem on AAPL')).toBeInTheDocument();
    });

    it('filter buttons use DS Button component', () => {
        render(<MemoriesList memories={mockMemories} />);

        // Only the filter pills (All, Events, Decisions, Post-Mortems) + Show Flow toggle
        const filterButtons = screen.getAllByRole('button');
        const dsButtons = filterButtons.filter((btn) =>
            ['All', 'Events', 'Decisions', 'Post-Mortems', 'Show Flow', 'Hide Flow'].includes(
                btn.textContent || '',
            ),
        );
        expect(dsButtons.length).toBeGreaterThanOrEqual(5);

        for (const btn of dsButtons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });

    it('filters memories by type when button is clicked', () => {
        render(<MemoriesList memories={mockMemories} />);

        const eventsButton = screen.getByText('Events');
        fireEvent.click(eventsButton);

        expect(screen.getByText('Consensus on rate hike')).toBeInTheDocument();
        expect(screen.queryByText('Decision to buy TSLA')).not.toBeInTheDocument();
        expect(screen.queryByText('Post-mortem on AAPL')).not.toBeInTheDocument();

        const decisionsButton = screen.getByText('Decisions');
        fireEvent.click(decisionsButton);

        expect(screen.queryByText('Consensus on rate hike')).not.toBeInTheDocument();
        expect(screen.getByText('Decision to buy TSLA')).toBeInTheDocument();
    });

    it('displays metadata badges correctly', () => {
        render(<MemoriesList memories={mockMemories} />);
        expect(screen.getByText('BEARISH')).toBeInTheDocument();
        expect(screen.getByText('$TSLA')).toBeInTheDocument();
        expect(screen.getByText('Regret')).toBeInTheDocument();
    });

    it('shows empty state when no memories match filter', () => {
        render(<MemoriesList memories={[]} />);
        expect(screen.getByText('No memories found in this category')).toBeInTheDocument();
    });

    it('expands scenario analysis when button is clicked', () => {
        render(<MemoriesList memories={mockMemories} />);

        const analysisButton = screen.getByText('Show Analysis');
        expect(screen.queryByText('Scenario Analysis')).not.toBeInTheDocument();

        fireEvent.click(analysisButton);

        expect(screen.getByText('Scenario Analysis')).toBeInTheDocument();
        expect(screen.getByText('Buy bank stocks.')).toBeInTheDocument();
    });

    it('shows event chain link for memories with parent', () => {
        render(<MemoriesList memories={mockMemories} />);

        // Memory 2 has a parent
        expect(screen.getByText('View event chain →')).toBeInTheDocument();
    });

    describe('Real Database Memories Categorization & Filtering (TDD)', () => {
        const databaseMemories: Memory[] = [
            {
                id: 'db-cal-1',
                content: '[CALENDAR EVENT] (08:30) 2026-05-25: Core CPI',
                created_at: new Date().toISOString(),
                metadata: { is_calendar_event: true },
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'CALENDAR_EVENT',
                importance_score: null,
                target_date: null,
            },
            {
                id: 'db-pa-1',
                content: '5-DAY POST-ANALYSIS (AAPL): Keep hold because premium pricing is solid.',
                created_at: new Date().toISOString(),
                metadata: { analysis_window: '5', price_change_pct: 12.3 },
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'LESSON_LEARNED',
                importance_score: null,
                target_date: null,
            },
            {
                id: 'db-ap-1',
                content: 'EMPIRICAL ASSET PRICING PRINCIPLE: Sloan Accrual Anomaly',
                created_at: new Date().toISOString(),
                metadata: { source_type: 'academic_paper' },
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'LESSON_LEARNED',
                importance_score: null,
                target_date: null,
            },
            {
                id: 'db-ll-1',
                content: 'Avoid trading on extreme leverage during high volatility days.',
                created_at: new Date().toISOString(),
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'LESSON_LEARNED',
                importance_score: null,
                target_date: null,
            },
        ];

        it('filters by Calendar Events correctly', () => {
            render(<MemoriesList memories={databaseMemories} />);
            const btn = screen.getByText('Calendar Events');
            expect(btn).toBeInTheDocument();
            fireEvent.click(btn);
            expect(screen.getByText(/Core CPI/)).toBeInTheDocument();
            expect(screen.queryByText(/POST-ANALYSIS/)).not.toBeInTheDocument();
        });

        it('filters by Post-Mortems correctly using analysis_window metadata', () => {
            render(<MemoriesList memories={databaseMemories} />);
            const btn = screen.getByText('Post-Mortems');
            expect(btn).toBeInTheDocument();
            fireEvent.click(btn);
            expect(screen.getByText(/POST-ANALYSIS/)).toBeInTheDocument();
            expect(screen.queryByText(/Core CPI/)).not.toBeInTheDocument();
            expect(screen.queryByText(/Sloan Accrual/)).not.toBeInTheDocument();
        });

        it('filters by Academic Principles correctly', () => {
            render(<MemoriesList memories={databaseMemories} />);
            const btn = screen.getByText('Principles');
            expect(btn).toBeInTheDocument();
            fireEvent.click(btn);
            expect(screen.getByText(/Sloan Accrual/)).toBeInTheDocument();
            expect(screen.queryByText(/POST-ANALYSIS/)).not.toBeInTheDocument();
        });

        it('filters by general Lessons correctly', () => {
            render(<MemoriesList memories={databaseMemories} />);
            const btn = screen.getByText('Lessons');
            expect(btn).toBeInTheDocument();
            fireEvent.click(btn);
            expect(screen.getByText(/extreme leverage/)).toBeInTheDocument();
            expect(screen.queryByText(/Sloan Accrual/)).not.toBeInTheDocument();
            expect(screen.queryByText(/POST-ANALYSIS/)).not.toBeInTheDocument();
        });
    });
});
