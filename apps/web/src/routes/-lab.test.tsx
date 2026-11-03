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

    it('renders the 3 category blocks and links to the retired agents page', () => {
        render(<LabDirectoryView />);

        expect(screen.getByText('Research & Prediction Engines')).toBeInTheDocument();
        expect(screen.getByText('Cognition & Market Telemetry')).toBeInTheDocument();
        expect(screen.getByText('Audits, Benchmarks & Retired Archives')).toBeInTheDocument();
        expect(screen.getByText('Auto-Research')).toBeInTheDocument();
        expect(screen.getByText('Memories')).toBeInTheDocument();

        const link = screen.getByText('Retired Agents').closest('a');
        expect(link).toHaveAttribute('href', '/retired-agents');
        expect(screen.queryByText('Retired Agent Archive')).not.toBeInTheDocument();
    });
});
