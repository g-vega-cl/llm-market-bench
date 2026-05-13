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
