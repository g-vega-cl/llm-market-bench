import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { Memory } from './MemoriesList';
import { MemoryCard } from './MemoryCard';

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        Link: ({ children, ...props }: any) => <a {...props}>{children}</a>,
    };
});

function makeMemory(overrides: Partial<Memory['metadata']> = {}): Memory {
    return {
        id: 'test-1',
        content: 'Fed signals potential rate cut in June',
        created_at: new Date().toISOString(),
        metadata: {
            type: 'consensus_event',
            impact: 'BULLISH',
            scenario_analysis:
                'Scenario A: 70% probability market rallies as rate cut boosts growth -> Trading Plan (How to Profit): Buy SPY. Scenario B: 30% probability stagflation fears cause sell-off -> Trading Plan (How to Profit): Buy GLD.',
            ...overrides,
        },
        status: 'ACTIVE',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        memory_type: 'MARKET_EVENT',
        importance_score: null,
        target_date: null,
    };
}

describe('MemoryCard scenario percentage badges', () => {
    it('renders percentage badge for scenario with embedded percentage', () => {
        render(<MemoryCard memory={makeMemory()} />);

        fireEvent.click(screen.getByText('Show Analysis'));

        expect(screen.getByText('70%')).toBeInTheDocument();
        expect(screen.getByText('30%')).toBeInTheDocument();
    });

    it('renders scenario analysis without percentages gracefully', () => {
        const memory = makeMemory({
            scenario_analysis:
                'Scenario A: Market rallies on positive data -> Trading Plan (How to Profit): Buy SPY. Scenario B: Market drops on negative data -> Trading Plan (How to Profit): Buy bonds.',
        });

        render(<MemoryCard memory={memory} />);

        fireEvent.click(screen.getByText('Show Analysis'));

        expect(screen.getByText('Scenario A:')).toBeInTheDocument();
        expect(screen.getByText('Scenario B:')).toBeInTheDocument();
        expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    });

    it('renders percentage badge when percentage is in parentheses', () => {
        const memory = makeMemory({
            scenario_analysis:
                'Scenario A: (65%) Bullish continuation -> Trading Plan (How to Profit): Buy QQQ.',
        });

        render(<MemoryCard memory={memory} />);

        fireEvent.click(screen.getByText('Show Analysis'));

        expect(screen.getByText('65%')).toBeInTheDocument();
    });

    it('renders percentage badge for new format "Scenario A (XX% probability):"', () => {
        const memory = makeMemory({
            scenario_analysis:
                'Scenario A (85% probability): Massive rally -> Trading Plan (How to Profit): Long call options.',
        });

        render(<MemoryCard memory={memory} />);

        fireEvent.click(screen.getByText('Show Analysis'));

        expect(screen.getByText('85%')).toBeInTheDocument();
        // The "Scenario A" text should be present without the probability suffix
        expect(screen.getByText('Scenario A:')).toBeInTheDocument();
    });

    it('does not show analysis section when no scenario_analysis', () => {
        const memory = makeMemory();
        memory.metadata!.scenario_analysis = undefined;

        render(<MemoryCard memory={memory} />);

        expect(screen.queryByText('Show Analysis')).not.toBeInTheDocument();
    });
});
