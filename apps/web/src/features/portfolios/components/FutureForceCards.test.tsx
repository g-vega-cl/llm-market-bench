import type { PositionWithReasoning } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { FutureForce } from '../api/fetch-portfolios';
import { FutureForceCards } from './FutureForceCards';

const mockForces: FutureForce[] = [
    {
        id: 'f1',
        portfolio_id: 'sys-future-forces',
        force_title: 'Hormuz Energy & Tanker Squeeze',
        archetype: 'geopolitical_chokepoint',
        thesis: 'Persian Gulf naval escalation doubles spot tanker charter rates.',
        catalyst_event: 'Q3 spot freight rate prints.',
        horizon_months: 3,
        invalidation_triggers: 'Bilateral maritime peace treaty signed.',
        transmission_mechanism: 'Spot rates flow straight to dividend yield.',
        tickers: ['FRO', 'STNG'],
        conviction_score: 5,
        status: 'active',
    },
    {
        id: 'f2',
        portfolio_id: 'sys-future-forces',
        force_title: 'FIFA World Cup 2026 Travel Squeeze',
        archetype: 'mega_event',
        thesis: 'Localized lodging shortages in North American host cities.',
        catalyst_event: 'Advance ticket lotteries and booking acceleration.',
        horizon_months: 9,
        invalidation_triggers: 'Municipal bans on short term rentals.',
        transmission_mechanism: 'Surge ADR and booking fee collection.',
        tickers: ['ABNB'],
        conviction_score: 4,
        status: 'pending_liquidation',
    },
];

const mockPositions: PositionWithReasoning[] = [
    {
        position_id: '1',
        portfolio_id: 'sys-future-forces',
        owner_id: 'sys-future-forces',
        ticker: 'FRO',
        quantity: 100,
        average_cost_basis: 20.0,
        current_price: 25.0,
        price_fetched_at: '2026-09-25',
        unrealized_pnl_usd: 500,
        unrealized_pnl_pct: 25.0,
        reasoning: 'Hormuz tanker squeeze proxy.',
    },
];

describe('FutureForceCards', () => {
    it('renders force title, archetype, tickers, and invalidation triggers', () => {
        render(<FutureForceCards forces={mockForces} positions={mockPositions} />);

        expect(screen.getByText('Hormuz Energy & Tanker Squeeze')).toBeInTheDocument();
        expect(screen.getByText(/Geopolitical Chokepoint/i)).toBeInTheDocument();
        expect(screen.getByText('3m Horizon')).toBeInTheDocument();
        expect(screen.getByText('Conviction 5/5')).toBeInTheDocument();
        expect(screen.getByText('FRO')).toBeInTheDocument();
        expect(screen.getByText('STNG')).toBeInTheDocument();
        expect(screen.getByText('Bilateral maritime peace treaty signed.')).toBeInTheDocument();

        // Check pending liquidation badge on f2
        expect(screen.getByText('Pending Market Open')).toBeInTheDocument();
    });

    it('renders null when forces array is empty', () => {
        const { container } = render(<FutureForceCards forces={[]} positions={[]} />);
        expect(container.firstChild).toBeNull();
    });
});
