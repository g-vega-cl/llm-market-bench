import {
    Badge,
    Button,
    MetricTile,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
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
    });

    describe('Box Sizing Standardization (Equal-Sized Grids)', () => {
        it('HomePage dashboard container enforces equal-height stretched columns', () => {
            const mockData: HomePageData = {
                portfolios: [],
                benchmark: { todayPct: 0.5, weekPct: 1.2 },
            };
            render(<HomePage data={mockData} />);
            const dashboard = screen.getByTestId('dashboard');
            expect(dashboard.className).toContain('items-stretch');
            expect(dashboard.className).not.toContain('items-start');
        });

        it('LabDirectoryView enforces equal-sized category block grid', () => {
            render(<LabDirectoryView retiredPortfolios={[]} />);
            const categoryGrid = screen.getByTestId('lab-category-grid');
            expect(categoryGrid.className).toContain('grid');
            expect(categoryGrid.className).toContain('items-stretch');
            expect(categoryGrid.className).not.toContain('items-start');
        });
    });
});
