import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { type Trade, TradesTable } from './TradesTable';

const mockTrades: Trade[] = [
    {
        id: 't1',
        portfolio_id: 'p1',
        ticker: 'AAPL',
        signal: 'BUY',
        quantity: 10,
        price: 150,
        total_cost: 1500,
        executed_at: '2026-01-01T12:00:00Z',
        alpaca_status: 'FILLED',
        alpaca_order_id: 'alpaca-order-1',
        alpaca_submitted_at: '2026-01-01T12:00:00Z',
        alpaca_filled_at: '2026-01-01T12:05:00Z',
        audit_flag: null,
        audit_note: null,
        realized_pnl: null,
        realized_pnl_pct: null,
        reasoning: 'Bullish momentum breakout.',
        decision_id: 'd1',
    },
    {
        id: 't2',
        portfolio_id: 'p1',
        ticker: 'TSLA',
        signal: 'SELL',
        quantity: 5,
        price: 700,
        total_cost: 3500,
        executed_at: '2026-01-02T12:00:00Z',
        alpaca_status: 'CANCELED',
        alpaca_order_id: 'alpaca-order-2',
        alpaca_submitted_at: '2026-01-02T12:00:00Z',
        alpaca_filled_at: null,
        audit_flag: null,
        audit_note: null,
        realized_pnl: 100,
        realized_pnl_pct: 2.86,
        reasoning: 'Taking profit at target.',
        decision_id: 'd2',
    },
];

describe('TradesTable', () => {
    it('renders all trades in the table', () => {
        render(<TradesTable trades={mockTrades} />);
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.getByText('TSLA')).toBeInTheDocument();
        expect(screen.getByText('BUY')).toBeInTheDocument();
        expect(screen.getByText('SELL')).toBeInTheDocument();
        expect(screen.getByText('FILLED')).toBeInTheDocument();
        expect(screen.getByText('CANCELED')).toBeInTheDocument();
    });

    it('expands reasoning when a row is clicked', () => {
        render(<TradesTable trades={mockTrades} />);
        expect(screen.queryByText('Bullish momentum breakout.')).not.toBeInTheDocument();
        const aaplRow = screen.getByText('AAPL').closest('tr');
        expect(aaplRow).toBeInTheDocument();
        if (aaplRow) {
            fireEvent.click(aaplRow);
            expect(screen.getByText('Bullish momentum breakout.')).toBeInTheDocument();
            expect(screen.getByText('Thinking Process')).toBeInTheDocument();
            fireEvent.click(aaplRow);
            expect(screen.queryByText('Bullish momentum breakout.')).not.toBeInTheDocument();
        }
    });

    it('renders exact execution time and date in the table column and cells', () => {
        render(<TradesTable trades={mockTrades} />);
        expect(screen.getByText('Executed At')).toBeInTheDocument();
        expect(screen.getByText('Jan 1, 2026')).toBeInTheDocument();
        const timeElements = screen.getAllByText('7:00:00 AM ET');
        expect(timeElements.length).toBeGreaterThanOrEqual(1);
    });

    it('displays exact execution and filled timestamps in the expanded trade view', () => {
        render(<TradesTable trades={mockTrades} />);
        const aaplRow = screen.getByText('AAPL').closest('tr');
        expect(aaplRow).toBeInTheDocument();
        if (aaplRow) {
            fireEvent.click(aaplRow);
            expect(screen.getByText(/Alpaca Filled:/i)).toBeInTheDocument();
            expect(screen.getByText(/7:05:00 AM ET/)).toBeInTheDocument();
        }
    });

    it('applies the min-width to the inner table rather than the container', () => {
        const { container } = render(<TradesTable trades={mockTrades} />);
        const outerWrapper = container.firstChild as HTMLElement;
        expect(outerWrapper).toBeInTheDocument();
        expect(outerWrapper.className).not.toContain('min-w-[700px]');

        const table = container.querySelector('table');
        expect(table).toBeInTheDocument();
        expect(table?.className).toContain('min-w-[700px]');
    });

    it('renders execution trace when trade has metadata.execution_trace', () => {
        const tradeWithTrace: Trade = {
            ...mockTrades[0],
            id: 't-trace',
            ticker: 'NVDA',
            signal: 'BUY',
            price: 115,
            reasoning: 'AI demand thesis',
            metadata: {
                execution_trace: {
                    active_source_ids: ['src_99'],
                    newsletters: [
                        {
                            source_id: 'src_99',
                            sender: 'Reuters Technology',
                            subject: 'Chip Demand Update',
                        },
                    ],
                    tools_called: [
                        {
                            tool: 'get_stock_quote',
                            ticker: 'NVDA',
                        },
                    ],
                },
            },
        };

        render(<TradesTable trades={[tradeWithTrace]} />);
        const row = screen.getByText('NVDA').closest('tr');
        expect(row).toBeInTheDocument();
        if (row) {
            fireEvent.click(row);
            expect(screen.getByText('Execution Provenance & Grounding')).toBeInTheDocument();
            expect(screen.getByText('get_stock_quote: NVDA')).toBeInTheDocument();
            expect(screen.getByText(/Chip Demand Update/)).toBeInTheDocument();
        }
    });

    it('renders BACKFILLED provenance in the expanded row instead of a tooltip', () => {
        const backfilledTrade: Trade = {
            ...mockTrades[0],
            id: 't-backfill',
            ticker: 'SPY',
            alpaca_status: 'BACKFILLED',
            alpaca_order_id: null,
            alpaca_filled_at: null,
            audit_flag: null,
            audit_note: null,
        };

        render(<TradesTable trades={[backfilledTrade]} />);
        const badge = screen.getByText('BACKFILLED');
        expect(badge).toBeInTheDocument();
        expect(badge).not.toHaveAttribute('title');
        expect(badge.closest('a')).toBeNull();

        fireEvent.click(screen.getByRole('button', { name: 'Inspect SPY trade' }));
        expect(
            screen.getByText('Reconstructed post-market via historical session bars'),
        ).toBeInTheDocument();
    });
});

describe('TradesTable realized P/L sign', () => {
    it('renders a negative dollar P/L with a leading minus sign', () => {
        const losingTrade: Trade = {
            ...mockTrades[0],
            id: 't-loss',
            ticker: 'SPY',
            signal: 'SELL',
            realized_pnl: -64.42,
            realized_pnl_pct: -2.24,
        };
        render(<TradesTable trades={[losingTrade]} />);
        expect(screen.getByText('-$64.42')).toBeInTheDocument();
        expect(screen.getByText('-2.24%')).toBeInTheDocument();
        expect(screen.queryByText('+$64.42')).not.toBeInTheDocument();
    });
});

describe('TradesTable audit annotations', () => {
    it('renders a holiday badge for non-trading-day fills', () => {
        const flagged: Trade = {
            ...mockTrades[0],
            audit_flag: 'NON_TRADING_DAY',
            audit_note: 'Executed 2026-11-26 with no US equity session.',
        };
        render(<TradesTable trades={[flagged]} />);
        expect(screen.getByText('HOLIDAY')).toBeInTheDocument();
        expect(screen.queryByText('BAD_PRICE')).not.toBeInTheDocument();
    });

    it('renders a bad-price badge for fills outside the session range', () => {
        const flagged: Trade = {
            ...mockTrades[0],
            audit_flag: 'PRICE_OUTSIDE_DAY_RANGE',
            audit_note: 'Fill is 9.96% outside the session range.',
        };
        render(<TradesTable trades={[flagged]} />);
        expect(screen.getByText('BAD_PRICE')).toBeInTheDocument();
    });

    it('exposes audit evidence in flow through a keyboard-reachable inspect control', () => {
        const flagged: Trade = {
            ...mockTrades[0],
            audit_flag: 'PRICE_OUTSIDE_DAY_RANGE',
            audit_note: 'Fill is 9.96% outside the session range.',
        };
        render(<TradesTable trades={[flagged]} />);

        const note = flagged.audit_note ?? '';
        const badge = screen.getByText('BAD_PRICE');
        expect(badge).not.toHaveAttribute('title');
        const inspect = screen.getByRole('button', { name: 'Inspect AAPL trade' });
        expect(inspect).toHaveAttribute('aria-expanded', 'false');
        expect(screen.queryByText(note)).not.toBeInTheDocument();

        fireEvent.click(inspect);

        expect(inspect).toHaveAttribute('aria-expanded', 'true');
        expect(screen.getByText('AUDIT EVIDENCE')).toBeInTheDocument();
        expect(screen.getByText(note)).toBeInTheDocument();
        expect(document.querySelector('[title]')).toBeNull();
    });
});
