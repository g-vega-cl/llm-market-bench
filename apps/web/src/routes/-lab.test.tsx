import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LAB_CATEGORIES, LabDirectoryView } from './lab';

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

describe('LabDirectoryView (/lab)', () => {
    it('defines strictly 3 category blocks covering all experimental and legacy routes', () => {
        expect(LAB_CATEGORIES).toHaveLength(3);
        const allPaths = LAB_CATEGORIES.flatMap((c) => c.items.map((i) => i.to));
        expect(allPaths).toContain('/autoresearch');
        expect(allPaths).toContain('/memories');
        expect(allPaths).toContain('/daily-predictions');
        expect(allPaths).toContain('/barometer-audit');
        expect(allPaths).toContain('/audits');
    });

    it('renders the 3 category blocks with descriptions and retired portfolios archive', () => {
        const mockRetired = [
            {
                id: 'ret-1',
                owner_id: 'gemini-3.1-pro-preview',
                cash_balance: 45000,
                buying_power: 45000,
                total_equity: 98500,
                last_updated_at: '2026-01-01',
                excess_liquidity: 45000,
                maintenance_margin: 0,
                realized: 0,
                sma: 45000,
            },
        ];

        render(<LabDirectoryView retiredPortfolios={mockRetired} />);

        expect(screen.getByText('Research & Prediction Engines')).toBeInTheDocument();
        expect(screen.getByText('Cognition & Market Telemetry')).toBeInTheDocument();
        expect(screen.getByText('Audits, Benchmarks & Retired Archives')).toBeInTheDocument();

        // Check link descriptions exist
        expect(screen.getByText('Auto-Research')).toBeInTheDocument();
        expect(screen.getByText('Memories')).toBeInTheDocument();

        // Check retired portfolio is listed in the archive
        expect(screen.getByText('gemini-3.1-pro-preview')).toBeInTheDocument();
    });
});
