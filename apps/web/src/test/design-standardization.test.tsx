import {
    Badge,
    Button,
    MetricTile,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LiveAgentConsole } from '~/features/home/components/LiveAgentConsole';
import { HomePage, type HomePageData } from '~/features/home/pages/HomePage';
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

        it('LabDirectoryView enforces equal-sized category block grid and intrinsic fluid tracks', () => {
            const { container } = render(<LabDirectoryView retiredPortfolios={[]} />);
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
    });
});
