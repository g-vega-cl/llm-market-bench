import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type {
    EarningsAlphaSnapshot,
    SectorBellwetherSignal,
} from '../features/earnings/api/fetch-earnings-audit';
import { EarningsAuditPage } from '../features/earnings/pages/EarningsAuditPage';

const mockSnapshots: EarningsAlphaSnapshot[] = [
    {
        id: '1',
        snapshot_date: '2026-08-30',
        ticker: 'NVDA',
        sector: 'XLK',
        report_date: '2026-08-26',
        actual_eps: 2.22,
        estimated_eps: 2.09,
        eps_surprise: 0.13,
        revenue_actual: 96221000000,
        revenue_estimated: 92270940000,
        revenue_surprise_pct: 4.28,
        sue_score: 5.3,
        is_top_decile_sue: true,
        quarters_analyzed_count: 8,
        has_sufficient_earnings_history: true,
        sloan_accrual_ratio: -0.02,
        is_sloan_accrual_clean: true,
        has_extreme_pre_earnings_runup: false,
        pre_earnings_20d_return_pct: 12.0,
        days_since_earnings_report: 4,
        post_earnings_drift_pct: 5.2,
        post_earnings_alpha_vs_spy: 3.8,
        analyst_consensus: 'Buy',
        analyst_coverage_count: 79,
        analyst_buy_ratio_pct: 75.9,
        target_consensus_price: 345.21,
        target_consensus_upside_pct: 15.0,
    },
    {
        id: '2',
        snapshot_date: '2026-08-30',
        ticker: 'JPM',
        sector: 'XLF',
        report_date: '2026-07-14',
        actual_eps: 7.59,
        estimated_eps: 5.59,
        eps_surprise: 2.0,
        revenue_actual: 57347000000,
        revenue_estimated: 50720640000,
        revenue_surprise_pct: 13.06,
        sue_score: 7.77,
        is_top_decile_sue: true,
        quarters_analyzed_count: 8,
        has_sufficient_earnings_history: true,
        sloan_accrual_ratio: 0.05,
        is_sloan_accrual_clean: true,
        has_extreme_pre_earnings_runup: false,
        pre_earnings_20d_return_pct: 5.0,
        days_since_earnings_report: 47,
        post_earnings_drift_pct: 8.4,
        post_earnings_alpha_vs_spy: 6.1,
        analyst_consensus: 'Buy',
        analyst_coverage_count: 61,
        analyst_buy_ratio_pct: 52.5,
        target_consensus_price: 240.0,
        target_consensus_upside_pct: 10.5,
    },
];

const mockBellwethers: SectorBellwetherSignal[] = [
    {
        id: '1',
        snapshot_date: '2026-08-30',
        sector: 'XLK',
        ticker: 'NVDA',
        classification: 'EARLY_BELLWETHER',
        market_cap: 3000000000000,
        market_cap_rank: 1,
        report_date: '2026-08-26',
        cycle_report_day: 4,
        is_reported: true,
        is_active_bellwether_signal: true,
        sue_score: 5.3,
        revenue_surprise_pct: 4.28,
        operating_margin_surprise_delta: 2.5,
    },
];

describe('EarningsAuditPage', () => {
    it('renders audit page titles, metrics, and PEAD table', () => {
        render(<EarningsAuditPage snapshots={mockSnapshots} bellwethers={mockBellwethers} />);

        expect(screen.getByText('Earnings Alpha & PEAD Audit')).toBeInTheDocument();
        expect(screen.getByText('NVDA')).toBeInTheDocument();
        expect(screen.getByText('JPM')).toBeInTheDocument();
        expect(screen.getByText('+5.30')).toBeInTheDocument();
        expect(screen.getByText('+7.77')).toBeInTheDocument();
        expect(screen.getAllByText('Top Decile')).toHaveLength(2);
    });

    it('filters snapshots by search term', () => {
        render(<EarningsAuditPage snapshots={mockSnapshots} bellwethers={mockBellwethers} />);

        const searchInput = screen.getByPlaceholderText('Search ticker or sector...');
        fireEvent.change(searchInput, { target: { value: 'NVDA' } });

        expect(screen.getByText('NVDA')).toBeInTheDocument();
        expect(screen.queryByText('JPM')).not.toBeInTheDocument();
    });

    it('switches to bellwether radar and revision tabs', () => {
        render(<EarningsAuditPage snapshots={mockSnapshots} bellwethers={mockBellwethers} />);

        // Click Bellwether tab
        const bellwetherTab = screen.getByText('Sector Bellwether Radar');
        fireEvent.click(bellwetherTab);

        expect(screen.getByText('Early Bellwether')).toBeInTheDocument();
        expect(screen.getByText('Active Signal (14d)')).toBeInTheDocument();

        // Click Revisions tab
        const revisionsTab = screen.getByText('Analyst Revision Momentum');
        fireEvent.click(revisionsTab);

        expect(screen.getByText('79 analysts')).toBeInTheDocument();
        expect(screen.getByText('75.9%')).toBeInTheDocument();
    });
});
