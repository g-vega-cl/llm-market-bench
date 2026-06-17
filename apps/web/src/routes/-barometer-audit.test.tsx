import type { MarketBarometer } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BarometerAuditPage } from '../features/home/pages/BarometerAuditPage';

// Mock Router
const mockNavigate = vi.fn();
vi.mock('@tanstack/react-router', () => ({
    useNavigate: () => mockNavigate,
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

const mockBarometer: MarketBarometer = {
    date: '2026-06-17',
    pe_ratio: 25.5,
    forward_pe: 21.2,
    pb_ratio: 4.8,
    ps_ratio: 3.2,
    earnings_surprise_momentum: 75.0,
    updated_at: '2026-06-17T16:00:00Z',
    constituents_data: [
        {
            symbol: 'AAPL',
            company_name: 'Apple Inc.',
            market_cap: 3000000000000,
            price: 200.0,
            pe: 30.0,
            pb: 45.0,
            ps: 8.0,
            next_eps_est: 8.0,
            beat: true,
        },
        {
            symbol: 'MSFT',
            company_name: 'Microsoft Corp',
            market_cap: 3200000000000,
            price: 400.0,
            pe: 35.0,
            pb: 12.0,
            ps: 11.0,
            next_eps_est: 12.0,
            beat: false,
        },
        {
            symbol: 'NVDA',
            company_name: 'NVIDIA Corp',
            market_cap: 2800000000000,
            price: 120.0,
            pe: 60.0,
            pb: 25.0,
            ps: 22.0,
            next_eps_est: null,
            beat: null,
        },
    ] as MarketBarometer['constituents_data'],
};

describe('BarometerAuditPage', () => {
    it('renders audit page titles, aggregates, and constituent table correctly', () => {
        render(
            <BarometerAuditPage
                dates={['2026-06-17', '2026-06-16']}
                selectedDate="2026-06-17"
                barometer={mockBarometer}
            />,
        );

        // Assert title and aggregates render
        expect(screen.getByText('Market Health Barometer Audit')).toBeInTheDocument();
        expect(screen.getByText('Trailing P/E')).toBeInTheDocument();
        expect(screen.getByText('25.50')).toBeInTheDocument();
        expect(screen.getByText('Forward P/E')).toBeInTheDocument();
        expect(screen.getByText('21.20')).toBeInTheDocument();

        // Assert table rows render
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
        expect(screen.getByText('$3.00T')).toBeInTheDocument();
        expect(screen.getByText('BEAT')).toBeInTheDocument();

        expect(screen.getByText('MSFT')).toBeInTheDocument();
        expect(screen.getByText('Microsoft Corp')).toBeInTheDocument();
        expect(screen.getByText('$3.20T')).toBeInTheDocument();
        expect(screen.getByText('MISS')).toBeInTheDocument();
    });

    it('filters constituents by search term', () => {
        render(
            <BarometerAuditPage
                dates={['2026-06-17']}
                selectedDate="2026-06-17"
                barometer={mockBarometer}
            />,
        );

        const searchInput = screen.getByPlaceholderText('Search by Ticker/Name...');
        expect(searchInput).toBeInTheDocument();

        // Search for 'AAPL'
        fireEvent.change(searchInput, { target: { value: 'AAPL' } });

        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.queryByText('MSFT')).not.toBeInTheDocument();
    });

    it('filters constituents by earnings beat status dropdown', () => {
        render(
            <BarometerAuditPage
                dates={['2026-06-17']}
                selectedDate="2026-06-17"
                barometer={mockBarometer}
            />,
        );

        const select = screen.getByLabelText('Filter Earnings Status');

        // Select 'Beats Only'
        fireEvent.change(select, { target: { value: 'beat' } });

        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.queryByText('MSFT')).not.toBeInTheDocument();
        expect(screen.queryByText('NVDA')).not.toBeInTheDocument();

        // Select 'Misses Only'
        fireEvent.change(select, { target: { value: 'miss' } });

        expect(screen.queryByText('AAPL')).not.toBeInTheDocument();
        expect(screen.getByText('MSFT')).toBeInTheDocument();
        expect(screen.queryByText('NVDA')).not.toBeInTheDocument();

        // Select 'No Data Only'
        fireEvent.change(select, { target: { value: 'na' } });

        expect(screen.queryByText('AAPL')).not.toBeInTheDocument();
        expect(screen.queryByText('MSFT')).not.toBeInTheDocument();
        expect(screen.getByText('NVDA')).toBeInTheDocument();
    });

    it('shows warning/empty state when no constituent data is present', () => {
        const legacyBarometer: MarketBarometer = {
            ...mockBarometer,
            constituents_data: null,
        };

        render(
            <BarometerAuditPage
                dates={['2026-06-17']}
                selectedDate="2026-06-17"
                barometer={legacyBarometer}
            />,
        );

        expect(screen.getByText('No Constituent-Level Data Available')).toBeInTheDocument();
        expect(screen.queryByText('AAPL')).not.toBeInTheDocument();
    });
});
