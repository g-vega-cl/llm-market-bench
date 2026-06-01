import { render, screen } from '@testing-library/react';
import type React from 'react';
import { describe, expect, it } from 'vitest';
import { MarketStatusHero } from './MarketStatusHero';

const baseData = {
    trades: [],
    decisions: [],
    memories: [],
    priceUpdates: [],
    futureEvents: [],
    newsletters: [],
    marketFeeling: {
        id: 'mf-1',
        sentiment_label: 'Bullish',
        sentiment_emoji: '🐂',
        market_direction: 'BULLISH',
        confidence_score: 75,
        why_explanation: 'Macro tailwinds.',
        primary_concern: 'Inflation',
        created_at: '2026-06-01T14:00:00Z',
        model_used: 'gpt-5',
        formattedTime: '10:00 AM ET',
    },
    serverTime: '2026-06-01T14:00:00Z',
    isMarketOpen: true,
    isSentimentStale: true,
    todayDateString: 'Monday, June 1, 2026',
} as unknown as React.ComponentProps<typeof MarketStatusHero>['data'];

describe('MarketStatusHero accessibility (color contrast)', () => {
    it('does not use the failing text-amber-300 class on a dark glass surface for the stale badge', () => {
        render(<MarketStatusHero data={baseData} />);
        // The stale badge is the only place text-amber-300 was previously used.
        // After the fix, the class should be a higher-contrast token (e.g. text-amber-200)
        // or removed entirely. We assert it does not contain the failing class.
        const container = screen.getByTitle('Data is older than 4 hours');
        expect(container.className).not.toMatch(/text-amber-300/);
        // The new contrast class must exist on the same element
        expect(container.className).toMatch(/text-amber-(?:100|200|400)/);
    });
});
