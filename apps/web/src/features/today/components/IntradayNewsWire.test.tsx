import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { FormattedIntradayNews } from '../api/fetch-intraday-news';
import { IntradayNewsWire } from './IntradayNewsWire';

const makeNewsItem = (overrides: Partial<FormattedIntradayNews> = {}): FormattedIntradayNews => ({
    id: 'news-1',
    headline: 'ISM Services PMI Accelerates to 54.9 vs 51.5 Consensus',
    summary: 'Inflationary pressure in services reignites bond yield spike.',
    source: 'FMP Macro Calendar',
    url: 'https://example.com/ism',
    tickers: ['SPY', 'QQQ', 'TLT'],
    event_timestamp: '2026-10-05T14:00:00Z',
    jev_choice: 'MARKET_MOVING',
    jev_confidence: 92.0,
    source_id_hash: 'hash123',
    created_at: '2026-10-05T14:02:00Z',
    formattedTime: '10:00 AM',
    formattedDate: 'October 5, 2026',
    ...overrides,
});

describe('IntradayNewsWire', () => {
    describe('empty state', () => {
        it('renders heading and standby message when items array is empty', () => {
            render(<IntradayNewsWire items={[]} />);
            expect(screen.getByText('⚡ Intraday Market Wire')).toBeInTheDocument();
            expect(
                screen.getByText('No breaking catalysts detected yet today'),
            ).toBeInTheDocument();
        });

        it('renders standby message when items is undefined or null', () => {
            // @ts-expect-error test undefined input
            render(<IntradayNewsWire items={null} />);
            expect(
                screen.getByText('No breaking catalysts detected yet today'),
            ).toBeInTheDocument();
        });
    });

    describe('populated state', () => {
        it('renders headline, source, and Jev confidence badge', () => {
            const item = makeNewsItem();
            render(<IntradayNewsWire items={[item]} />);

            expect(
                screen.getByText('ISM Services PMI Accelerates to 54.9 vs 51.5 Consensus'),
            ).toBeInTheDocument();
            expect(screen.getByText(/10:00 AM ET/)).toBeInTheDocument();
            expect(screen.getByText('FMP Macro Calendar')).toBeInTheDocument();
            expect(screen.getByText(/⚡ MARKET_MOVING 92%/)).toBeInTheDocument();
        });

        it('renders ticker badges for affected equities', () => {
            const item = makeNewsItem();
            render(<IntradayNewsWire items={[item]} />);

            expect(screen.getByText('$SPY')).toBeInTheDocument();
            expect(screen.getByText('$QQQ')).toBeInTheDocument();
            expect(screen.getByText('$TLT')).toBeInTheDocument();
        });

        it('renders source link when url is present', () => {
            const item = makeNewsItem({ url: 'https://example.com/full-story' });
            render(<IntradayNewsWire items={[item]} />);

            const link = screen.getByRole('link', { name: /Source/i });
            expect(link).toBeInTheDocument();
            expect(link).toHaveAttribute('href', 'https://example.com/full-story');
        });
    });
});
