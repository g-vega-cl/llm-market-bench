import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { HomePageData } from './HomePage';
import { HomePage } from './HomePage';

// Mock PostHog
const mockGetFeatureFlag = vi.fn();
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        getFeatureFlag: mockGetFeatureFlag,
        onFeatureFlags: vi.fn((cb) => cb()), // Instantly call callback for tests
    }),
}));

describe('HomePage Dashboard', () => {
    it('should render the Liquid Glass dashboard layout and individual portfolio cards without a manual background selector', () => {
        // Set up the experiment to return pointillism
        mockGetFeatureFlag.mockReturnValue('pointillism');

        const mockData: HomePageData = {
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
                summary:
                    'The market is experiencing positive momentum due to strong tech earnings.',
                sentimentLabel: 'Risk-On Rally',
                sentimentEmoji: '🚀',
                confidence: 85,
                primaryConcern: 'Inflation risks',
                secondaryConcern: 'Yield curve steepening',
                modelUsed: 'MiniMax-Text-01',
                lastAnalyzed: '14:30:00 ET',
            },
        };

        // We also need to mock getContext to prevent canvas errors when ShaderBackground mounts
        HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
            createShader: vi.fn(),
            shaderSource: vi.fn(),
            compileShader: vi.fn(),
            getShaderParameter: vi.fn().mockReturnValue(true),
            createProgram: vi.fn(),
            attachShader: vi.fn(),
            linkProgram: vi.fn(),
            getProgramParameter: vi.fn().mockReturnValue(true),
            useProgram: vi.fn(),
            createBuffer: vi.fn(),
            bindBuffer: vi.fn(),
            bufferData: vi.fn(),
            getAttribLocation: vi.fn().mockReturnValue(0),
            enableVertexAttribArray: vi.fn(),
            vertexAttribPointer: vi.fn(),
            getUniformLocation: vi.fn().mockReturnValue(0),
            viewport: vi.fn(),
            uniform2f: vi.fn(),
            uniform1f: vi.fn(),
            uniform3f: vi.fn(),
            drawArrays: vi.fn(),
            deleteProgram: vi.fn(),
            deleteShader: vi.fn(),
            deleteBuffer: vi.fn(),
        }) as unknown as typeof HTMLCanvasElement.prototype.getContext;

        render(<HomePage data={mockData} />);

        // Verify the main title exists
        expect(screen.getByText('Market Overview')).toBeDefined();

        // The background selector should be entirely removed
        expect(screen.queryByRole('combobox')).toBeNull();

        // Verify the background image no longer exists
        expect(screen.queryByTestId('background-image')).toBeNull();
        expect(screen.queryByTestId('background-video')).toBeNull();

        const desktopContainer = screen.getByTestId('desktop-dashboard');

        // Verify individual portfolios render and apply correct heatmap styling & truncation wrapping
        const claudeHeading = within(desktopContainer).getByText('Claude 3 Opus');
        expect(claudeHeading).toBeDefined();
        expect(claudeHeading.className).not.toContain('truncate');
        expect(claudeHeading.parentElement?.className).toContain('overflow-hidden');
        const claudeCard = claudeHeading.closest('div.group');
        expect(claudeCard).toBeDefined();
        expect(claudeCard).toHaveAttribute('data-color-scheme', 'danger');

        expect(within(desktopContainer).getAllByText('Auto-Research').length).toBeGreaterThan(0);
        expect(within(desktopContainer).getAllByText('Active').length).toBeGreaterThan(0);
        expect(within(desktopContainer).getByText('$32.98')).toBeDefined();
        expect(within(desktopContainer).getByText('-4.5%')).toBeDefined();

        const llamaHeading = within(desktopContainer).getByText('Llama 3 70B');
        expect(llamaHeading).toBeDefined();
        expect(llamaHeading.className).not.toContain('truncate');
        expect(llamaHeading.parentElement?.className).toContain('overflow-hidden');
        const llamaCard = llamaHeading.closest('div.group');
        expect(llamaCard).toBeDefined();
        expect(llamaCard).toHaveAttribute('data-color-scheme', 'warning');

        expect(within(desktopContainer).getByText('+2%')).toBeDefined();

        const gptHeading = within(desktopContainer).getByText('Gpt 5.4 Nano');
        expect(gptHeading).toBeDefined();
        expect(gptHeading.className).not.toContain('truncate');
        expect(gptHeading.parentElement?.className).toContain('overflow-hidden');
        const gptCard = gptHeading.closest('div.group');
        expect(gptCard).toBeDefined();
        expect(gptCard).toHaveAttribute('data-color-scheme', 'info');

        // Verify S&P 500 Benchmark card renders
        const spHeading = within(desktopContainer).getByText('S&P 500');
        expect(spHeading).toBeDefined();
        expect(spHeading.className).not.toContain('truncate');
        expect(spHeading.parentElement?.className).toContain('overflow-hidden');
        expect(within(desktopContainer).getByText('+1.2%')).toBeDefined(); // Today
        expect(within(desktopContainer).getByText('+2.5%')).toBeDefined(); // Week

        // Verify LLM Feeling card renders
        expect(within(desktopContainer).getByText('BULLISH')).toBeDefined();
        expect(within(desktopContainer).getByText(/strong tech earnings/)).toBeDefined();
        expect(within(desktopContainer).getByText('Risk-On Rally')).toBeDefined();
        expect(within(desktopContainer).getByText('🚀')).toBeDefined();
        expect(within(desktopContainer).getByText('⚠️ Inflation risks')).toBeDefined();
        expect(within(desktopContainer).getByText('🔍 Yield curve steepening')).toBeDefined();
        expect(within(desktopContainer).getByText(/Last analyzed: 14:30:00 ET/)).toBeDefined();
        expect(within(desktopContainer).getByText(/Model: MiniMax-Text-01/)).toBeDefined();
    });

    it('should render the high-density mobile layout with collapsible market feeling and dense model table', () => {
        mockGetFeatureFlag.mockReturnValue('pointillism');

        const mockData: HomePageData = {
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
            ],
            benchmark: {
                todayPct: 1.2,
                weekPct: 2.5,
            },
            feeling: {
                sentiment: 'BULLISH',
                summary: 'The market is experiencing positive momentum.',
                sentimentLabel: 'Risk-On Rally',
                sentimentEmoji: '🚀',
                confidence: 85,
                primaryConcern: 'Inflation risks',
                secondaryConcern: 'Yield curve steepening',
                modelUsed: 'MiniMax-Text-01',
                lastAnalyzed: '14:30:00 ET',
            },
        };

        render(<HomePage data={mockData} />);

        const mobileContainer = screen.getByTestId('mobile-dashboard');

        // Verify mobile dashboard elements are present
        expect(within(mobileContainer).getByText('Live Overview')).toBeDefined();
        expect(within(mobileContainer).getByText('S&P 500 Benchmark')).toBeDefined();

        // Collapsible trigger should exist
        const toggleBtn = within(mobileContainer).getByText('🧠 Market Feeling Analysis');
        expect(toggleBtn).toBeDefined();

        // Table headers should exist
        expect(within(mobileContainer).getByText('Active Agent Portfolios')).toBeDefined();
        expect(within(mobileContainer).getByText('Model')).toBeDefined();
        expect(within(mobileContainer).getByText('Equity')).toBeDefined();
        expect(within(mobileContainer).getByText('Today / Wk')).toBeDefined();

        // Verify model info exists in mobile table
        expect(within(mobileContainer).getByText('Claude 3 Opus')).toBeDefined();
        expect(within(mobileContainer).getByText('$32.98')).toBeDefined();
        expect(within(mobileContainer).getByText('-4.5%')).toBeDefined();
        expect(within(mobileContainer).getByText('-1.2% wk')).toBeDefined();

        expect(within(mobileContainer).getByText('Llama 3 70B')).toBeDefined();
        expect(within(mobileContainer).getByText('$23.89')).toBeDefined();
        expect(within(mobileContainer).getByText('+2%')).toBeDefined();
        expect(within(mobileContainer).getByText('+5.1% wk')).toBeDefined();
    });
});
