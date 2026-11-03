import {
    Badge,
    Button,
    EmptyState,
    ErrorCard,
    Input,
    Label,
    MetricTile,
    SectionHeading,
    Select,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ScoreCalculation } from '~/features/autoresearch/components/ScoreCalculation';
import { DailyMetricsOverview } from '~/features/daily-predictions/components/DailyMetricsOverview';
import { HeroPredictionCard } from '~/features/daily-predictions/components/HeroPredictionCard';
import { LiveAgentConsole } from '~/features/home/components/LiveAgentConsole';
import { HomePage, type HomePageData } from '~/features/home/pages/HomePage';
import { LeaderboardPodium } from '~/features/leaderboard/components/LeaderboardPodium';
import { LabDirectoryView } from '~/routes/lab';

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        Link: ({
            to,
            params,
            children,
            className,
        }: {
            to: string;
            params?: Record<string, string>;
            children: React.ReactNode;
            className?: string;
        }) => {
            const href = params?.portfolioId ? to.replace('$portfolioId', params.portfolioId) : to;
            return (
                <a href={href} className={className}>
                    {children}
                </a>
            );
        },
    };
});

describe('Design Standardization: Typography & Box Sizing', () => {
    describe('Typography Standardization (Strict 3 Combinations)', () => {
        it('SectionHeading renders with Tier 1 typography (text-lg font-bold)', () => {
            render(<SectionHeading>Test Heading</SectionHeading>);
            const heading = screen.getByRole('heading', { level: 2, name: /Test Heading/i });
            expect(heading.className).toContain('text-lg');
            expect(heading.className).toContain('font-bold');
            expect(heading.className).not.toContain('text-2xl');
            expect(heading.className).not.toContain('font-black');
        });

        it('Button renders with Tier 2 typography (text-sm font-bold)', () => {
            render(<Button>Click Me</Button>);
            const btn = screen.getByRole('button', { name: 'Click Me' });
            expect(btn.className).toContain('text-sm');
            expect(btn.className).toContain('font-bold');
        });

        it('SubHeading renders with Tier 2 typography (text-sm font-bold)', () => {
            render(<SubHeading>Sub Title</SubHeading>);
            const sub = screen.getByText('Sub Title');
            expect(sub.className).toContain('text-sm');
            expect(sub.className).toContain('font-bold');
            expect(sub.className).not.toContain('text-xl');
        });

        it('Badge renders without arbitrary text-[9px] or text-[10px] escapes', () => {
            render(<Badge size="xs">Tag</Badge>);
            const badge = screen.getByText('Tag');
            expect(badge.className).not.toContain('text-[9px]');
            expect(badge.className).not.toContain('text-[10px]');
            expect(badge.className).toContain('text-sm');
            expect(badge.className).toContain('font-bold');
        });

        it('Badge solid accent enforces high-contrast text and container gap without manual child margins', () => {
            const { container } = render(
                <Badge variant="solid" colorScheme="accent" showDot>
                    NEUTRAL
                </Badge>,
            );
            const badge = container.firstChild as HTMLElement;
            // High contrast check: must use dark Tatami/Trough text, never white
            expect(badge.className).toContain('text-boxel-trough');
            expect(badge.className).not.toContain('text-white');
            // Gap check: must use container gap, no manual margin on dot
            expect(badge.className).toContain('gap-1.5');
            const dot = badge.querySelector('span');
            if (dot) {
                expect(dot.className).not.toContain('mr-1.5');
            }
        });

        it('MetricTile conforms to sharp voxel-trough boxel styling and eliminates rounded-xl and text-[9px]', () => {
            const { container } = render(<MetricTile label="Total Return" value="+12.5%" />);
            const tile = container.firstChild as HTMLElement;
            expect(tile.className).toContain('voxel-trough');
            expect(tile.className).toContain('rounded-none');
            expect(tile.className).not.toContain('rounded-xl');
            expect(tile.className).not.toContain('text-[9px]');

            const label = screen.getByText('Total Return');
            expect(label.className).toContain('text-xs');
            expect(label.className).toContain('font-normal');

            const val = screen.getByText('+12.5%');
            expect(val.className).toContain('text-sm');
            expect(val.className).toContain('font-bold');
            expect(val.className).not.toContain('text-lg');
            expect(val.className).not.toContain('font-black');
        });
        it('LiveAgentConsole renders NEUTRAL market direction with neutral colorScheme', () => {
            render(
                <LiveAgentConsole
                    bars={[]}
                    agentState={{
                        action: 'HOLD',
                        conviction: 50,
                        thought: 'Testing neutral',
                        marketDirection: 'NEUTRAL',
                    }}
                />,
            );
            const badge = screen.getByText('NEUTRAL').closest('.voxel-badge') as HTMLElement;
            expect(badge).toBeDefined();
            expect(badge.getAttribute('data-color-scheme') ?? badge.className).toMatch(/neutral/);
            expect(badge.className).not.toContain('bg-accent');
        });

        it('ErrorCard conforms to boxel geometry rounded-none and Tier 2/3 typography', () => {
            const { container } = render(
                <ErrorCard
                    title="Feed Error"
                    message="Unable to load market feeds"
                    onRetry={() => {}}
                />,
            );
            const card = container.firstChild as HTMLElement;
            expect(card.className).toContain('rounded-none');
            expect(card.className).not.toContain('rounded-xl');

            const title = screen.getByRole('heading', { level: 3, name: /Feed Error/i });
            expect(title.className).toContain('text-sm');
            expect(title.className).toContain('font-bold');

            const msg = screen.getByText('Unable to load market feeds');
            expect(msg.className).toContain('text-xs');
            expect(msg.className).toContain('font-normal');
            expect(msg.className).not.toContain('text-sm');

            const btn = screen.getByRole('button', { name: /Retry/i });
            expect(btn.className).toContain('text-sm');
            expect(btn.className).toContain('font-bold');
            expect(btn.className).not.toContain('rounded-lg');
        });

        it('EmptyState conforms to Tier 1 title, Tier 3 subtitle, and gap-only flow without text-6xl or mb-*', () => {
            const { container } = render(
                <EmptyState
                    emoji="📊"
                    title="No Active Orders"
                    subtitle="There are no pending market executions in this window."
                />,
            );
            const title = screen.getByRole('heading', { level: 2, name: /No Active Orders/i });
            expect(title.className).toContain('text-lg');
            expect(title.className).toContain('font-bold');
            expect(title.className).not.toContain('text-2xl');
            expect(title.className).not.toContain('text-3xl');
            expect(title.className).not.toContain('font-black');
            expect(title.className).not.toMatch(/\bmb-[0-9]+/);

            const subtitle = screen.getByText(
                'There are no pending market executions in this window.',
            );
            expect(subtitle.className).toContain('text-xs');
            expect(subtitle.className).toContain('font-normal');
            expect(subtitle.className).not.toContain('text-base');
            expect(subtitle.className).not.toMatch(/\bmb-[0-9]+/);

            expect(container.innerHTML).not.toContain('text-6xl');
            expect(container.innerHTML).not.toContain('text-7xl');
        });

        it('Input and Select use rounded-none and Label uses Tier 2 text-sm font-bold', () => {
            const { container } = render(
                <div>
                    <Label>Ticker Symbol</Label>
                    <Input placeholder="SPY" />
                    <Select options={['1D', '1W']} />
                </div>,
            );
            const label = screen.getByText('Ticker Symbol');
            expect(label.className).toContain('text-sm');
            expect(label.className).toContain('font-bold');
            expect(label.className).not.toContain('font-semibold');

            const inputWrapper = container.querySelector('input')?.parentElement;
            expect(inputWrapper?.className).toContain('rounded-none');
            expect(inputWrapper?.className).not.toContain('rounded-xl');

            const selectWrapper = container.querySelector('select')?.parentElement;
            expect(selectWrapper?.className).toContain('rounded-none');
            expect(selectWrapper?.className).not.toContain('rounded-xl');
        });
    });

    describe('Box Sizing & Layout Standardization (Equal Grids & Gap-Only Flow)', () => {
        it('HomePage dashboard container enforces equal-height stretched columns and container gap flow', () => {
            const mockData: HomePageData = {
                portfolios: [],
                benchmark: { todayPct: 0.5, weekPct: 1.2 },
            };
            const { container } = render(<HomePage data={mockData} />);
            const dashboard = screen.getByTestId('dashboard');
            expect(dashboard.className).toContain('items-stretch');
            expect(dashboard.className).not.toContain('items-start');

            // Header does not use manual bottom margin, PageLayout owns spacing via gap
            const header = container.querySelector('header');
            expect(header).not.toBeNull();
            expect(header?.className).not.toMatch(/\bmb-[0-9]+/);
        });

        it('LeaderboardPodium enforces equal-height stretched cards without arbitrary min-h variations', () => {
            const mockModels = [
                {
                    model_name: 'anthropic/claude-3.5-sonnet',
                    composite_score: 85.5,
                    total_trades: 120,
                    win_rate: 65,
                    daily_excess_return: 0.12,
                    sharpe_ratio: 1.8,
                    max_drawdown: 0.05,
                    return_pct: 15.2,
                    consistency_score: 85.0,
                },
                {
                    model_name: 'openai/gpt-4o',
                    composite_score: 82.1,
                    total_trades: 110,
                    win_rate: 62,
                    daily_excess_return: 0.1,
                    sharpe_ratio: 1.6,
                    max_drawdown: 0.06,
                    return_pct: 11.4,
                    consistency_score: 82.0,
                },
                {
                    model_name: 'deepseek/deepseek-chat',
                    composite_score: 79.4,
                    total_trades: 95,
                    win_rate: 58,
                    daily_excess_return: 0.08,
                    sharpe_ratio: 1.4,
                    max_drawdown: 0.07,
                    return_pct: 8.7,
                    consistency_score: 79.0,
                },
            ];
            const { container } = render(
                <LeaderboardPodium
                    models={
                        mockModels as unknown as Parameters<typeof LeaderboardPodium>[0]['models']
                    }
                />,
            );
            const podiumContainer = container.firstChild as HTMLElement;
            expect(podiumContainer.className).toContain('items-stretch');
            expect(podiumContainer.className).not.toContain('items-end');

            // Must not contain hardcoded unequal height classes
            expect(container.innerHTML).not.toContain('min-h-[400px]');
            expect(container.innerHTML).not.toContain('min-h-[350px]');
            expect(container.innerHTML).not.toContain('min-h-[320px]');
        });

        it('DailyMetricsOverview enforces equal-sized items-stretch grid without text-2xl', () => {
            const { container } = render(
                <DailyMetricsOverview
                    accuracyPct="65.4"
                    intradayHitPct="42.0"
                    correctCount={17}
                    totalEvaluated={26}
                    avgBrier="0.1850"
                    totalPredictions={50}
                    activePromptTag="variant-v2-active"
                />,
            );
            const grid = container.firstChild as HTMLElement;
            expect(grid.className).toContain('items-stretch');
            expect(grid.className).toContain('grid');
            expect(container.innerHTML).not.toContain('text-2xl');
        });

        it('LabDirectoryView enforces equal-sized category block grid and intrinsic fluid tracks', () => {
            const { container } = render(<LabDirectoryView />);
            const categoryGrid = screen.getByTestId('lab-category-grid');
            expect(categoryGrid.className).toContain('grid');
            expect(categoryGrid.className).toContain('items-stretch');
            expect(categoryGrid.className).not.toContain('items-start');
            expect(categoryGrid.className).toContain('minmax(min(100%,20rem),1fr)');

            // Header does not use manual bottom margin, PageLayout owns spacing via gap
            const header = container.querySelector('header');
            expect(header).not.toBeNull();
            expect(header?.className).not.toMatch(/\bmb-[0-9]+/);
        });

        it('HeroPredictionCard conforms to rounded-none and strict 3-tier typography without text-4xl or mb-*', () => {
            const mockPrediction = {
                id: 'pred-1',
                target_date: '2026-11-03',
                ticker: 'SPY',
                predicted_direction: 'UP' as const,
                confidence: 85,
                expected_return_pct: 1.5,
                rationale: 'Strong momentum and earnings surprises.',
                catalysts: ['FOMC', 'CPI'],
                status: 'pending' as const,
                created_at: '2026-11-03T08:00:00Z',
            };
            const { container } = render(
                <HeroPredictionCard
                    prediction={
                        mockPrediction as unknown as Parameters<
                            typeof HeroPredictionCard
                        >[0]['prediction']
                    }
                />,
            );
            expect(container.innerHTML).not.toContain('text-4xl');
            expect(container.innerHTML).not.toContain('font-black');
            expect(container.innerHTML).not.toContain('rounded-2xl');
            expect(container.innerHTML).not.toMatch(/\bmb-[0-9]+/);
        });

        it('ScoreCalculation conforms to sharp boxel geometry and 3-tier typography without text-3xl', () => {
            const { container } = render(<ScoreCalculation />);
            expect(container.innerHTML).not.toContain('text-3xl');
            expect(container.innerHTML).not.toContain('text-2xl');
            expect(container.innerHTML).not.toContain('rounded-2xl');
            const formulaBlock = container.querySelector('.font-mono');
            expect(formulaBlock?.className).toContain('text-lg');
            expect(formulaBlock?.className).toContain('font-bold');
        });
    });
});
