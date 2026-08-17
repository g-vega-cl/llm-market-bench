import { describe, expect, it } from 'vitest';

/**
 * Tests for TradeActivity component filter logic.
 *
 * Win #3: Today Feed "Executed" Filter
 * TradeActivity now supports an 'EXECUTED' filter type that shows only
 * successful trades (excluding rejections).
 */

type FilterType = 'ALL' | 'BUY' | 'SELL' | 'REJECTED' | 'EXECUTED';

interface ActivityItem {
    type: 'TRADE' | 'REJECTION';
    signal?: 'BUY' | 'SELL';
}

function filterActivity(activity: ActivityItem[], filter: FilterType): ActivityItem[] {
    if (filter === 'ALL') return activity;
    if (filter === 'BUY')
        return activity.filter((item) => item.type === 'TRADE' && item.signal === 'BUY');
    if (filter === 'SELL')
        return activity.filter((item) => item.type === 'TRADE' && item.signal === 'SELL');
    if (filter === 'REJECTED') return activity.filter((item) => item.type === 'REJECTION');
    if (filter === 'EXECUTED') return activity.filter((item) => item.type === 'TRADE');
    return activity;
}

describe('TradeActivity filter logic', () => {
    const mockActivity: ActivityItem[] = [
        { type: 'TRADE', signal: 'BUY' },
        { type: 'TRADE', signal: 'SELL' },
        { type: 'REJECTION' },
        { type: 'TRADE', signal: 'BUY' },
        { type: 'REJECTION' },
    ];

    it('ALL filter returns all activity', () => {
        const result = filterActivity(mockActivity, 'ALL');
        expect(result).toHaveLength(5);
    });

    it('BUY filter returns only BUY trades', () => {
        const result = filterActivity(mockActivity, 'BUY');
        expect(result).toHaveLength(2);
        expect(result.every((item) => item.type === 'TRADE' && item.signal === 'BUY')).toBe(true);
    });

    it('SELL filter returns only SELL trades', () => {
        const result = filterActivity(mockActivity, 'SELL');
        expect(result).toHaveLength(1);
        expect(result.every((item) => item.type === 'TRADE' && item.signal === 'SELL')).toBe(true);
    });

    it('REJECTED filter returns only rejections', () => {
        const result = filterActivity(mockActivity, 'REJECTED');
        expect(result).toHaveLength(2);
        expect(result.every((item) => item.type === 'REJECTION')).toBe(true);
    });

    it('EXECUTED filter returns only trades (not rejections)', () => {
        const result = filterActivity(mockActivity, 'EXECUTED');
        expect(result).toHaveLength(3);
        expect(result.every((item) => item.type === 'TRADE')).toBe(true);
    });

    it('EXECUTED filter excludes rejections', () => {
        const result = filterActivity(mockActivity, 'EXECUTED');
        const hasRejections = result.some((item) => item.type === 'REJECTION');
        expect(hasRejections).toBe(false);
    });
});

import { fireEvent, render, screen } from '@testing-library/react';
import { TradeActivity } from './TradeActivity';

describe('TradeActivity nested decision resolution', () => {
    it('resolves reasoning from nested decisions attached to trade object', () => {
        const mockTrade = {
            id: 'trade-1',
            executed_at: '2026-06-26T14:30:54Z',
            signal: 'BUY',
            ticker: 'USO',
            price: 105.56,
            decisions: [
                {
                    id: 'dec-1',
                    ticker: 'USO',
                    signal: 'BUY',
                    created_at: '2026-06-26T14:30:50Z',
                    reasoning: 'Nested decision reasoning for USO BUY',
                    model_name: 'MiniMax-M3',
                },
            ],
        };

        render(<TradeActivity trades={[mockTrade]} decisions={[]} />);
        fireEvent.click(screen.getByText('USO'));
        expect(screen.getByText('Nested decision reasoning for USO BUY')).toBeInTheDocument();
    });

    it('resolves reasoning from trade object when decision is null (e.g. system dust cleanup)', () => {
        const mockTrade = {
            id: 'trade-dust-1',
            executed_at: '2026-08-17T14:30:54Z',
            signal: 'SELL',
            ticker: 'BX',
            quantity: 6,
            price: 135.0,
            decision_id: null,
            reasoning:
                'Automatic dust position cleanup: Position value below 10% of portfolio equity',
        };

        render(<TradeActivity trades={[mockTrade]} decisions={[]} />);
        fireEvent.click(screen.getByText('BX'));
        expect(
            screen.getByText(
                'Automatic dust position cleanup: Position value below 10% of portfolio equity',
            ),
        ).toBeInTheDocument();
    });
});

describe('TradeActivity stats rendering', () => {
    it('correctly calculates total activity count (trades + rejections) in the Total pill', () => {
        const mockTrades = [
            {
                id: 'trade-1',
                executed_at: '2026-06-26T14:30:54Z',
                signal: 'BUY',
                ticker: 'USO',
                price: 105.56,
            },
        ];
        const mockDecisions = [
            {
                id: 'dec-1',
                ticker: 'USO',
                signal: 'BUY',
                created_at: '2026-06-26T14:30:50Z',
                status: 'REJECTED_RISK',
            },
            {
                id: 'dec-2',
                ticker: 'AAPL',
                signal: 'SELL',
                created_at: '2026-06-26T14:30:51Z',
                status: 'REJECTED_MARGIN',
            },
        ];

        render(<TradeActivity trades={mockTrades} decisions={mockDecisions} />);

        // Find Total button and check its value (should be 3)
        const totalButton = screen.getByRole('button', { name: /Total/i });
        expect(totalButton).toHaveTextContent('3');

        // Find Executed button and check its value (should be 1)
        const executedButton = screen.getByRole('button', { name: /Executed/i });
        expect(executedButton).toHaveTextContent('1');

        // Find Rejected button and check its value (should be 2)
        const rejectedButton = screen.getByRole('button', { name: /Rejected/i });
        expect(rejectedButton).toHaveTextContent('2');
    });
});
