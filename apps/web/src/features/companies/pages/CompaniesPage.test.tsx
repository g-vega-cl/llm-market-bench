import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { CompanySummaryItem } from '../api/fetch-companies';
import { CompaniesPage } from './CompaniesPage';

vi.mock('@tanstack/react-router', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    Link: ({ children, to }: any) => <a href={to}>{children}</a>,
}));

const mockCompanies: CompanySummaryItem[] = [
    {
        ticker: 'NVDA',
        company_name: 'NVIDIA Corp',
        sector: 'Semiconductors',
        is_sector_etf: false,
        entity_type: 'stock',
        latest_verdict: 'bullish',
        latest_conviction: 88,
        latest_date: '2026-11-10',
        formatted_date: 'November 10, 2026',
        spot_price_at_report: 138.25,
        mention_count: 5,
    },
    {
        ticker: 'SMH',
        company_name: 'VanEck Semiconductor ETF',
        sector: 'Semiconductors',
        is_sector_etf: true,
        entity_type: 'etf',
        latest_verdict: 'bullish',
        latest_conviction: 82,
        latest_date: '2026-11-10',
        formatted_date: 'November 10, 2026',
        spot_price_at_report: 242.1,
        mention_count: 8,
    },
    {
        ticker: 'INTC',
        company_name: 'Intel Corp',
        sector: 'Semiconductors',
        is_sector_etf: false,
        entity_type: 'stock',
        latest_verdict: 'bearish',
        latest_conviction: 75,
        latest_date: '2026-11-09',
        formatted_date: 'November 9, 2026',
        spot_price_at_report: 21.5,
        mention_count: 2,
    },
];

describe('CompaniesPage', () => {
    it('renders heading and empty state when no companies are available', () => {
        render(<CompaniesPage initialCompanies={[]} />);
        expect(screen.getByText('Company Intelligence & Research Dossiers')).toBeInTheDocument();
        expect(screen.getByText('No companies found')).toBeInTheDocument();
    });

    it('renders company cards with tickers, verdicts, and spot prices', () => {
        render(<CompaniesPage initialCompanies={mockCompanies} />);
        expect(screen.getByText('NVDA')).toBeInTheDocument();
        expect(screen.getByText('NVIDIA Corp')).toBeInTheDocument();
        expect(screen.getByText('SMH')).toBeInTheDocument();
        expect(screen.getByText('INTC')).toBeInTheDocument();
        expect(screen.getByText('$138.25')).toBeInTheDocument();
        expect(screen.getByText('8 briefings')).toBeInTheDocument();
    });

    it('filters companies by search query', () => {
        render(<CompaniesPage initialCompanies={mockCompanies} />);
        const searchInput = screen.getByPlaceholderText(/search by ticker/i);

        fireEvent.change(searchInput, { target: { value: 'Intel' } });
        expect(screen.getByText('INTC')).toBeInTheDocument();
        expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
    });

    it('filters companies by verdict tab', () => {
        render(<CompaniesPage initialCompanies={mockCompanies} />);
        const bearishFilter = screen.getByRole('button', { name: /^bearish$/i });

        fireEvent.click(bearishFilter);
        expect(screen.getByText('INTC')).toBeInTheDocument();
        expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
        expect(screen.queryByText('SMH')).not.toBeInTheDocument();
    });
});
