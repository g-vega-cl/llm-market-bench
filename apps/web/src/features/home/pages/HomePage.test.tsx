import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { HomePageData } from './HomePage';
import { HomePage } from './HomePage';

// Mock PostHog
const mockGetFeatureFlag = vi.fn();
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        getFeatureFlag: mockGetFeatureFlag,
        onFeatureFlags: vi.fn((cb) => cb()),
    }),
}));

// Mock Router
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
        sentimentEmoji: '🚀',
        confidence: 85,
        primaryConcern: 'Inflation risks',
        secondaryConcern: 'Yield curve steepening',
        modelUsed: 'MiniMax-Text-01',
        lastAnalyzed: '14:30:00 ET',
    },
};

describe('HomePage Dashboard', () => {
    it('renders the unified dashboard with header, sentiment info, S&P 500 benchmark, and portfolio table', () => {
        render(<HomePage data={baseData} />);

        const dashboard = screen.getByTestId('dashboard');

        // Page title
        expect(screen.getByText('Market Overview')).toBeDefined();

        // Sentiment header
        expect(within(dashboard).getByText('Live Overview')).toBeDefined();
        expect(within(dashboard).getByText('BULLISH')).toBeDefined();
        expect(within(dashboard).getByText('🚀')).toBeDefined();
        expect(within(dashboard).getByText('Risk-On Rally')).toBeDefined();

        // S&P 500 benchmark inline row
        expect(within(dashboard).getByText('S&P 500 Benchmark')).toBeDefined();
        expect(within(dashboard).getByText('+1.2%')).toBeDefined();
        expect(within(dashboard).getByText('+2.5%')).toBeDefined();

        // Portfolio table header
        expect(within(dashboard).getByText('Active Agent Portfolios')).toBeDefined();
        expect(within(dashboard).getByText('Model')).toBeDefined();
        expect(within(dashboard).getByText('Equity')).toBeDefined();
        expect(within(dashboard).getByText('Today / Wk')).toBeDefined();

        // Portfolio rows
        expect(within(dashboard).getByText('Claude 3 Opus')).toBeDefined();
        expect(within(dashboard).getByText('$32.98')).toBeDefined();
        expect(within(dashboard).getByText('-4.5%')).toBeDefined();
        expect(within(dashboard).getByText('-1.2% wk')).toBeDefined();

        expect(within(dashboard).getByText('Llama 3 70B')).toBeDefined();
        expect(within(dashboard).getByText('$23.89')).toBeDefined();
        expect(within(dashboard).getByText('+2%')).toBeDefined();
        expect(within(dashboard).getByText('+5.1% wk')).toBeDefined();

        expect(within(dashboard).getByText('Gpt 5.4 Nano')).toBeDefined();
        expect(within(dashboard).getByText('$3.19')).toBeDefined();
        expect(within(dashboard).getByText('-0.8%')).toBeDefined();
        expect(within(dashboard).getByText('+1.5% wk')).toBeDefined();
    });

    it('renders the market feeling collapsible toggle and shows a preview when collapsed', () => {
        render(<HomePage data={baseData} />);

        const dashboard = screen.getByTestId('dashboard');

        // Collapsible button present and shows "Expand" by default
        const toggleBtn = within(dashboard).getByText('🧠 Market Feeling Analysis');
        expect(toggleBtn).toBeDefined();
        expect(within(dashboard).getByText('Expand Details ▼')).toBeDefined();

        // Preview (truncated summary) visible when collapsed
        expect(
            within(dashboard).getByText(/positive momentum due to strong tech earnings/),
        ).toBeDefined();
    });

    it('expands market feeling details when the toggle is clicked', () => {
        render(<HomePage data={baseData} />);

        const dashboard = screen.getByTestId('dashboard');
        const toggleBtn = within(dashboard).getByRole('button', {
            name: /Market Feeling Analysis/,
        });

        fireEvent.click(toggleBtn);

        // Full summary visible
        expect(within(dashboard).getByText(/strong tech earnings/)).toBeDefined();

        // Concerns
        expect(within(dashboard).getByText('⚠️ Inflation risks')).toBeDefined();
        expect(within(dashboard).getByText('🔍 Yield curve steepening')).toBeDefined();

        // Metadata
        expect(within(dashboard).getByText(/Last: 14:30:00 ET/)).toBeDefined();
        expect(within(dashboard).getByText(/Model: MiniMax-Text-01/)).toBeDefined();

        // Button now shows Collapse
        expect(within(dashboard).getByText('Collapse ▲')).toBeDefined();
    });

    it('does not render a separate mobile or desktop dashboard — only a single unified dashboard', () => {
        render(<HomePage data={baseData} />);

        expect(screen.queryByTestId('mobile-dashboard')).toBeNull();
        expect(screen.queryByTestId('desktop-dashboard')).toBeNull();
        expect(screen.getByTestId('dashboard')).toBeDefined();
    });

    it('marks auto-research portfolios with a purple dot and manual ones with slate', () => {
        render(<HomePage data={baseData} />);

        const dashboard = screen.getByTestId('dashboard');

        // Claude 3 Opus is auto-research → purple dot shown as "Auto-Res"
        const claudeRow = within(dashboard).getByText('Claude 3 Opus').closest('tr');
        expect(claudeRow).toBeDefined();
        if (claudeRow) expect(within(claudeRow).getByText('Auto-Res')).toBeDefined();

        // Llama is manual → "Manual"
        const llamaRow = within(dashboard).getByText('Llama 3 70B').closest('tr');
        expect(llamaRow).toBeDefined();
        if (llamaRow) expect(within(llamaRow).getByText('Manual')).toBeDefined();
    });

    it('applies desktop responsive styling classes for layout, fonts, and table padding', () => {
        render(<HomePage data={baseData} />);

        const dashboard = screen.getByTestId('dashboard');
        const container = dashboard.parentElement;
        expect(container?.className).toContain('md:max-w-4xl');
        expect(dashboard.className).toContain('md:px-8');
        expect(dashboard.className).toContain('md:py-8');
        expect(dashboard.className).toContain('md:rounded-2xl');
        expect(dashboard.className).toContain('md:border');

        const title = screen.getByText('Market Overview');
        expect(title.className).toContain('md:text-4xl');
    });

    it('renders the Market Health Barometer card when barometer data is provided', () => {
        const barometerData = {
            date: '2026-06-17',
            pe_ratio: 28.362798,
            forward_pe: 13.609154,
            pb_ratio: 6.701241,
            ps_ratio: 4.73962,
            earnings_surprise_momentum: 92.929292,
            updated_at: '2026-06-17T14:19:15Z',
            constituents_data: [],
        };
        const dataWithBarometer = {
            ...baseData,
            barometer: barometerData,
        };
        render(<HomePage data={dataWithBarometer} />);

        const dashboard = screen.getByTestId('dashboard');

        // Assert barometer section is rendered
        expect(within(dashboard).getByText('MARKET HEALTH BAROMETER (S&P 500)')).toBeDefined();
        expect(within(dashboard).getByText('28.36')).toBeDefined();
        expect(within(dashboard).getByText('13.61')).toBeDefined();
        expect(within(dashboard).getByText('6.70')).toBeDefined();
        expect(within(dashboard).getByText('4.74')).toBeDefined();
        expect(within(dashboard).getByText('92.9%')).toBeDefined();
        expect(within(dashboard).getByText('As of 2026-06-17')).toBeDefined();
    });
});
