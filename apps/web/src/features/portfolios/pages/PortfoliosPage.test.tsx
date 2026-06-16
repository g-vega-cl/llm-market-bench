import type { Portfolio } from '@llm-market-bench/database';
import { render, screen, waitFor } from '@testing-library/react';
import type * as React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { PortfoliosPage } from './PortfoliosPage';

// Mock Tanstack Query's useSuspenseQuery and useQuery to return the data directly
vi.mock('@tanstack/react-query', async (importOriginal) => {
    const original = await importOriginal<typeof import('@tanstack/react-query')>();
    const stubQuery = ({
        queryKey,
        initialData,
    }: {
        queryKey?: unknown[];
        initialData?: unknown;
    }) => {
        if (queryKey && queryKey[0] === 'portfolios' && queryKey[1] === 'list') {
            return { data: initialData };
        }
        if (queryKey && queryKey[0] === 'portfolios' && queryKey[1] === 'comparison') {
            return {
                data: initialData || {
                    portfolios: [],
                    startDate: '',
                    endDate: '',
                    benchmarkData: {},
                },
            };
        }
        return { data: initialData };
    };
    return {
        ...original,
        useSuspenseQuery: vi.fn().mockImplementation(stubQuery),
        useQuery: vi.fn().mockImplementation(stubQuery),
        keepPreviousData: original.keepPreviousData,
    };
});

// Mock Tanstack Router's Link
vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        className?: string;
    }) => (
        <a href={to} className={className} data-testid="portfolio-link">
            {children}
        </a>
    ),
}));

// Mock PostHog
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: vi.fn(),
    }),
}));

// Mock sub-components
vi.mock('../components/BenchmarkSelector', () => ({
    BenchmarkSelector: () => <div data-testid="benchmark-selector">Mock BenchmarkSelector</div>,
}));

vi.mock('../components/PortfolioComparisonChart', () => ({
    PortfolioComparisonChart: () => <div data-testid="portfolio-comparison-chart">Mock Chart</div>,
}));

const mockPortfolios = [
    {
        id: 'p1',
        owner_id: 'gemini-3-flash-preview',
        total_equity: 100000,
        cash_balance: 50000,
        buying_power: 100000,
        is_active: true,
        is_autoresearch: true,
        created_at: '2026-05-25T12:00:00.000Z',
        updated_at: '2026-05-25T12:00:00.000Z',
    },
    {
        id: 'p2',
        owner_id: 'gpt-4-retired',
        total_equity: 80000,
        cash_balance: 40000,
        buying_power: 80000,
        is_active: false,
        is_autoresearch: false,
        created_at: '2026-05-25T12:00:00.000Z',
        updated_at: '2026-05-25T12:00:00.000Z',
    },
] as unknown as (Portfolio & { is_active: boolean; is_autoresearch: boolean })[];

describe('PortfoliosPage Card Heights & Layout', () => {
    it('should style portfolio cards and links to ensure equal heights and aligned metrics', async () => {
        const fetchFn = vi.fn().mockResolvedValue(mockPortfolios);
        const comparisonFetchFn = vi.fn().mockResolvedValue({
            portfolios: [],
            startDate: '',
            endDate: '',
            benchmarkData: {},
        });

        render(
            <PortfoliosPage
                initialData={mockPortfolios}
                fetchFn={fetchFn}
                comparisonFetchFn={comparisonFetchFn}
            />,
        );

        await waitFor(() => {
            // Retrieve the links wrapping the cards
            const links = screen.getAllByTestId('portfolio-link');
            expect(links.length).toBe(2);

            for (const link of links) {
                // 1. The wrapper Link should have `h-full` to stretch in the CSS grid cell
                expect(link.className).toContain('h-full');

                // 2. The inner Card component (first child of the Link element) should have `h-full` and `flex flex-col`
                const cardElement = link.firstChild as HTMLElement;
                expect(cardElement).toBeDefined();
                expect(cardElement.className).toContain('h-full');
                expect(cardElement.className).toContain('flex');
                expect(cardElement.className).toContain('flex-col');

                // 3. The metrics block container inside Card should have `mt-auto` to align items at the bottom
                const metricsContainer = cardElement.querySelector('.space-y-4');
                expect(metricsContainer).not.toBeNull();
                expect(metricsContainer?.className).toContain('mt-auto');
            }
        });
    });
});
