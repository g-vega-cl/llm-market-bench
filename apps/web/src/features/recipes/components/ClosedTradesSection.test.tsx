import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { CompletedTradeRecord } from '../types';
import { ClosedTradesSection } from './ClosedTradesSection';

const sampleTrades: CompletedTradeRecord[] = [
    {
        ticker: 'NVDA',
        action: 'BUY',
        entry_time: '2026-11-10 09:30 ET',
        entry_price: 130,
        exit_time: '2026-11-11 15:30 ET',
        exit_price: 143,
        shares: 10,
        pnl_midpoint: 130,
        pnl_net: 125,
        return_pct_midpoint: 10,
        return_pct_net: 9.6,
        exit_reason: 'TARGET_HIT',
        catalyst_headline: 'Hyperscaler capex guidance raised',
        confidence: 92,
    },
    {
        ticker: 'AMD',
        action: 'BUY',
        entry_time: '2026-11-12 09:30 ET',
        entry_price: 160,
        exit_time: '2026-11-13 11:00 ET',
        exit_price: 152,
        shares: 5,
        pnl_midpoint: -40,
        pnl_net: -42,
        return_pct_midpoint: -5,
        return_pct_net: -5.25,
        exit_reason: 'STOP_LOSS',
        catalyst_headline: 'Sector pullback after macro print',
        confidence: 70,
    },
];

describe('ClosedTradesSection', () => {
    it('renders newest trades first up to limit and supports in-flow keyboard/click inspection', () => {
        render(<ClosedTradesSection trades={sampleTrades} limit={1} />);

        expect(screen.getByText(/Closed Trades \(2\)/)).toBeInTheDocument();
        expect(screen.getByText('BUY AMD')).toBeInTheDocument();
        expect(screen.queryByText('BUY NVDA')).not.toBeInTheDocument();

        const inspector = screen.getByTestId('closed-trade-inspector');
        expect(inspector).toHaveTextContent(/Select any trade row above/i);

        const row = screen.getByRole('button', { name: /Inspect AMD closed trade/i });
        fireEvent.keyDown(row, { key: 'Enter' });

        expect(inspector).toHaveTextContent('Sector pullback after macro print');
        expect(inspector).toHaveTextContent('Confidence: 70%');
        expect(inspector).toHaveTextContent('Shares: 5');

        fireEvent.click(row);
        expect(inspector).toHaveTextContent(/Select any trade row above/i);
    });
});
