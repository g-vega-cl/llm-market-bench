import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { HomePageData } from './HomePage';
import { HomePage } from './HomePage';

const mockGetFeatureFlag = vi.fn();
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        getFeatureFlag: mockGetFeatureFlag,
        onFeatureFlags: vi.fn((cb) => cb()),
    }),
}));

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

const baseData: HomePageData = {
    portfolios: [
        {
            name: 'Claude 3 Opus',
            todayPct: -4.5,
            weekPct: -1.2,
            totalEquity: 32.98,
            isActive: true,
            isAutoResearch: true,
        },
        {
            name: 'Llama 3 70B',
            todayPct: 2.0,
            weekPct: 5.1,
            totalEquity: 23.89,
            isActive: true,
            isAutoResearch: false,
        },
        {
            name: 'Gpt 5.4 Nano',
            todayPct: -0.8,
            weekPct: 1.5,
            totalEquity: 3.19,
            isActive: true,
            isAutoResearch: false,
        },
    ],
    benchmark: {
        todayPct: 1.2,
        weekPct: 2.5,
    },
    feeling: {
        sentiment: 'BULLISH',
        summary: 'The market is experiencing positive momentum due to strong tech earnings.',
        sentimentLabel: 'Risk-On Rally',
        confidence: 85,
        primaryConcern: 'Inflation risks',
        secondaryConcern: 'Yield curve steepening',
        modelUsed: 'MiniMax-Text-01',
        lastAnalyzed: '14:30:00 ET',
        buyCount: 4,
        sellCount: 1,
    },
};

describe('HomePage 2-Block Boxel Dashboard', () => {
    it('renders strictly 2 blocks (AI Market Feeling and Active Agent Portfolios) without collapsibles', () => {
        render(<HomePage data={baseData} />);

        const dashboard = screen.getByTestId('dashboard');
        const feelingBlock = within(dashboard).getByTestId('home-block-feeling');
        const portfoliosBlock = within(dashboard).getByTestId('home-block-portfolios');

        expect(feelingBlock).toBeInTheDocument();
        expect(portfoliosBlock).toBeInTheDocument();

        // Live Trader Console is flat and always visible (zero collapsibles)
        expect(within(feelingBlock).getByText('24/7 Autonomous SPY Trader')).toBeInTheDocument();
        expect(within(feelingBlock).getAllByText('BULLISH').length).toBeGreaterThanOrEqual(1);
        expect(within(feelingBlock).getByText('Risk-On Rally')).toBeInTheDocument();
        expect(
            within(feelingBlock).getByText(/positive momentum due to strong tech earnings/),
        ).toBeInTheDocument();
        expect(
            within(feelingBlock).getByText(/Grounded in 1 memory reference/i),
        ).toBeInTheDocument();
        expect(within(feelingBlock).getByText(/Turn: 14:30:00 ET/)).toBeInTheDocument();
        expect(within(feelingBlock).getByText(/Model: MiniMax-Text-01/)).toBeInTheDocument();
        expect(within(feelingBlock).queryByText(/Expand Details/i)).toBeNull();

        // Segmented confidence bar is rendered
        expect(within(feelingBlock).getAllByTestId('confidence-segment')).toHaveLength(10);

        // S&P 500 benchmark inline trough in Block 2
        expect(within(portfoliosBlock).getByText('S&P 500 Benchmark')).toBeInTheDocument();
        expect(within(portfoliosBlock).getByText('+1.2%')).toBeInTheDocument();
        expect(within(portfoliosBlock).getByText('+2.5%')).toBeInTheDocument();

        // Portfolio table header and rows
        expect(within(portfoliosBlock).getByText('Active Agent Portfolios')).toBeInTheDocument();
        expect(within(portfoliosBlock).getByText('Claude 3 Opus')).toBeInTheDocument();
        expect(within(portfoliosBlock).getByText('$32.98')).toBeInTheDocument();
        expect(within(portfoliosBlock).getByText('-4.5%')).toBeInTheDocument();
        expect(within(portfoliosBlock).getByText('-1.2% wk')).toBeInTheDocument();

        expect(within(portfoliosBlock).getByText('Llama 3 70B')).toBeInTheDocument();
        expect(within(portfoliosBlock).getByText('$23.89')).toBeInTheDocument();
    });

    it('excludes mechanical system (sys-*) portfolios from the Home Active Agent Portfolios block', () => {
        const dataWithSystem: HomePageData = {
            ...baseData,
            portfolios: [
                ...baseData.portfolios,
                {
                    name: 'Sys Pead Drift',
                    todayPct: 0.52,
                    weekPct: 1.15,
                    totalEquity: 10052.0,
                    isActive: true,
                    isAutoResearch: false,
                    isSystem: true,
                },
            ],
        };
        render(<HomePage data={dataWithSystem} />);

        const portfoliosBlock = screen.getByTestId('home-block-portfolios');
        expect(within(portfoliosBlock).getByText('Claude 3 Opus')).toBeInTheDocument();
        expect(within(portfoliosBlock).queryByText('Sys Pead Drift')).toBeNull();
    });

    it('marks auto-research portfolios as Auto-Res and standard ones as Manual', () => {
        render(<HomePage data={baseData} />);

        const dashboard = screen.getByTestId('dashboard');
        const claudeRow = within(dashboard).getByText('Claude 3 Opus').closest('tr');
        expect(claudeRow).toBeDefined();
        if (claudeRow) expect(within(claudeRow).getByText('Auto-Res')).toBeInTheDocument();

        const llamaRow = within(dashboard).getByText('Llama 3 70B').closest('tr');
        expect(llamaRow).toBeDefined();
        if (llamaRow) expect(within(llamaRow).getByText('Manual')).toBeInTheDocument();
    });

    it('uses intrinsic flex-wrap layout on dashboard without media query breakpoints', () => {
        render(<HomePage data={baseData} />);

        const dashboard = screen.getByTestId('dashboard');
        expect(dashboard.className).toContain('flex-wrap');
        expect(dashboard.className).not.toMatch(/\b(sm|md|lg|xl):/);
    });
});
