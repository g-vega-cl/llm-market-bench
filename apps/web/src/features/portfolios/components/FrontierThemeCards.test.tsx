import type { PositionWithReasoning } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { FrontierTheme } from '../api/fetch-portfolios';
import { FrontierThemeCards } from './FrontierThemeCards';
import { PositionsTable } from './PositionsTable';

const mockThemes: FrontierTheme[] = [
    {
        id: 't1',
        portfolio_id: 'sys-frontier-tech',
        theme_name: 'Silicon Photonics & Optical Interconnects',
        thesis: 'Replacing copper wires with optical interconnects for 800G/1.6T AI scaling.',
        catalysts: 'Optical transceiver volume ramps.',
        rubric_score: 4,
        status: 'active',
        tickers: ['POET', 'LWLG'],
    },
];

const mockPositions: PositionWithReasoning[] = [
    {
        position_id: '1',
        portfolio_id: 'sys-frontier-tech',
        owner_id: 'sys-frontier-tech',
        ticker: 'POET',
        quantity: 100,
        average_cost_basis: 5.0,
        current_price: 6.0,
        price_fetched_at: '2026-09-10',
        unrealized_pnl_usd: 100,
        unrealized_pnl_pct: 20.0,
        reasoning: 'Pure-play optical chiplet enabler.',
    },
];

describe('FrontierThemeCards', () => {
    it('renders theme details and tickers', () => {
        render(<FrontierThemeCards themes={mockThemes} positions={mockPositions} />);

        expect(screen.getByText('Silicon Photonics & Optical Interconnects')).toBeInTheDocument();
        expect(screen.getByText('Rubric 4/5')).toBeInTheDocument();
        expect(screen.getByText('POET')).toBeInTheDocument();
        expect(screen.getByText('LWLG')).toBeInTheDocument();
        expect(
            screen.getByText(
                'Replacing copper wires with optical interconnects for 800G/1.6T AI scaling.',
            ),
        ).toBeInTheDocument();
    });

    it('renders null when themes array is empty', () => {
        const { container } = render(<FrontierThemeCards themes={[]} positions={[]} />);
        expect(container.firstChild).toBeNull();
    });
});

describe('PositionsTable with Themes', () => {
    it('renders theme badge next to constituent ticker', () => {
        render(<PositionsTable positions={mockPositions} themes={mockThemes} />);
        expect(screen.getByText('POET')).toBeInTheDocument();
        expect(screen.getByText('Silicon Photonics & Optical Interconnects')).toBeInTheDocument();
    });
});
