import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { CompanyDossierData } from '../api/fetch-company-dossier';
import { CompanyDossierPage } from './CompanyDossierPage';

vi.mock('@tanstack/react-router', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    Link: ({ children, to }: any) => <a href={to}>{children}</a>,
}));

vi.mock('~/components/ui/MarkdownContent', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    MarkdownContent: ({ content }: any) => <div data-testid="markdown-content">{content}</div>,
}));

const mockDossier: CompanyDossierData = {
    ticker: 'NVDA',
    mentionCount: 6,
    latestReport: {
        id: 'rep-1',
        ticker: 'NVDA',
        company_name: 'NVIDIA Corp',
        sector: 'Semiconductors',
        is_sector_etf: false,
        entity_type: 'stock',
        session: 'open',
        date: '2026-11-10',
        formatted_date: 'November 10, 2026',
        verdict: 'bullish',
        conviction_score: 92,
        risk_reward_score: 3.8,
        target_horizon: '3-6 months',
        spot_price_at_report: 138.25,
        forward_5d_return: 0.035,
        forward_20d_return: null,
        valuation_summary: 'Forward P/E of 34x supported by hyperscaler CapEx backlog.',
        buffett_moat_analysis: {
            moat_rating: 'Wide',
            pricing_power: 'Exceptional',
            rationale: 'CUDA software moat creates massive switching costs.',
        },
        options_sentiment_summary: 'Call skew strongly elevated; IV/RV ratio 1.12.',
        catalyst_context: 'Morning briefing spotlighted Blackwell accelerator shipments.',
        falsification_triggers: [
            'Hyperscaler CapEx guidance cuts below $180B aggregate',
            'Gross margin compression below 71%',
        ],
        full_report_markdown: '# NVIDIA Institutional Research Dossier\nFull report text here...',
        created_at: '2026-11-10T09:15:00Z',
    },
    pastReports: [
        {
            id: 'rep-0',
            ticker: 'NVDA',
            company_name: 'NVIDIA Corp',
            sector: 'Semiconductors',
            is_sector_etf: false,
            entity_type: 'stock',
            session: 'close',
            date: '2026-10-25',
            formatted_date: 'October 25, 2026',
            verdict: 'neutral',
            conviction_score: 65,
            risk_reward_score: 2.1,
            target_horizon: '1-3 months',
            spot_price_at_report: 124.5,
            forward_5d_return: 0.012,
            forward_20d_return: 0.08,
            valuation_summary: 'Consolidation phase ahead of quarterly earnings.',
            buffett_moat_analysis: { moat_rating: 'Wide' },
            options_sentiment_summary: 'Elevated put hedging ahead of earnings.',
            catalyst_context: 'Earnings preview note.',
            falsification_triggers: ['Foundry supply bottlenecks'],
            full_report_markdown: '# Past Report from October',
            created_at: '2026-10-25T17:00:00Z',
        },
    ],
};

describe('CompanyDossierPage', () => {
    it('renders empty state when no report exists for ticker', () => {
        render(
            <CompanyDossierPage
                initialData={{
                    ticker: 'UNKNOWN',
                    latestReport: null,
                    pastReports: [],
                    mentionCount: 0,
                }}
            />,
        );
        expect(screen.getByText('No Research Dossier for UNKNOWN')).toBeInTheDocument();
    });

    it('renders active dossier header, verdict, moat, and triggers', () => {
        render(<CompanyDossierPage initialData={mockDossier} />);
        expect(screen.getByText('NVDA')).toBeInTheDocument();
        expect(screen.getByText('NVIDIA Corp')).toBeInTheDocument();
        expect(screen.getByText(/bullish • 92% Conviction/i)).toBeInTheDocument();
        expect(screen.getByText(/Moat: Wide/i)).toBeInTheDocument();
        expect(screen.getByText(/CUDA software moat/i)).toBeInTheDocument();
        expect(
            screen.getByText(/Hyperscaler CapEx guidance cuts below \$180B aggregate/i),
        ).toBeInTheDocument();
        expect(screen.getByText(/Featured in 6 briefings/i)).toBeInTheDocument();
        expect(screen.getByTestId('markdown-content')).toHaveTextContent(
            /NVIDIA Institutional Research Dossier/,
        );
    });

    it('switches between latest and historical report when timeline button clicked', () => {
        render(<CompanyDossierPage initialData={mockDossier} />);
        const pastBtn = screen.getByRole('button', {
            name: /October 25, 2026 \(CLOSE\) • neutral/i,
        });

        fireEvent.click(pastBtn);
        expect(screen.getByText(/neutral • 65% Conviction/i)).toBeInTheDocument();
        expect(screen.getByTestId('markdown-content')).toHaveTextContent(
            /Past Report from October/,
        );
    });
});
