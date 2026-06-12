import { render, screen } from '@testing-library/react';
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

        // Verify individual portfolios render
        expect(screen.getByText('Claude 3 Opus')).toBeDefined();
        expect(screen.getAllByText('Auto-Research').length).toBeGreaterThan(0);
        expect(screen.getAllByText('Active').length).toBeGreaterThan(0);
        expect(screen.getByText('$32.98')).toBeDefined();
        expect(screen.getByText('-4.5%')).toBeDefined();

        expect(screen.getByText('Llama 3 70B')).toBeDefined();
        expect(screen.getByText('+2%')).toBeDefined();

        expect(screen.getByText('Gpt 5.4 Nano')).toBeDefined();

        // Verify S&P 500 Benchmark card renders
        expect(screen.getByText('S&P 500')).toBeDefined();
        expect(screen.getByText('+1.2%')).toBeDefined(); // Today
        expect(screen.getByText('+2.5%')).toBeDefined(); // Week

        // Verify LLM Feeling card renders
        expect(screen.getByText('BULLISH')).toBeDefined();
        expect(screen.getByText(/strong tech earnings/)).toBeDefined();
    });
});
