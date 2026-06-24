import type { NewsletterSnapshot } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { NewsletterFeed } from './NewsletterFeed';

type NewsletterWithTime = NewsletterSnapshot & { formattedTime?: string };

const makeNewsletter = (overrides: Partial<NewsletterWithTime> = {}): NewsletterWithTime => ({
    id: 'nl-1',
    subject: 'Test Subject',
    content: 'Test newsletter content',
    sender: 'test@example.com',
    chunk_hash: 'abc123',
    date: '2025-06-24',
    ingested_at: '2025-06-24T09:00:00Z',
    source_id: 'src-1',
    formattedTime: '09:00 AM',
    ...overrides,
});

describe('NewsletterFeed', () => {
    describe('empty state', () => {
        it('renders the section heading when newsletters array is empty', () => {
            render(<NewsletterFeed newsletters={[]} />);
            expect(screen.getByText('Daily Intelligence Briefing')).toBeInTheDocument();
        });

        it('renders the empty-state message when newsletters array is empty', () => {
            render(<NewsletterFeed newsletters={[]} />);
            expect(screen.getByText('No briefings ingested yet today')).toBeInTheDocument();
        });

        it('does not render newsletter cards when array is empty', () => {
            render(<NewsletterFeed newsletters={[]} />);
            expect(screen.queryByText('Test Subject')).not.toBeInTheDocument();
        });
    });

    describe('populated state', () => {
        it('renders the section heading when newsletters are present', () => {
            render(<NewsletterFeed newsletters={[makeNewsletter()]} />);
            expect(screen.getByText('Daily Intelligence Briefing')).toBeInTheDocument();
        });

        it('renders newsletter subject', () => {
            render(
                <NewsletterFeed
                    newsletters={[makeNewsletter({ subject: 'Market Rally Incoming' })]}
                />,
            );
            expect(screen.getByText('Market Rally Incoming')).toBeInTheDocument();
        });

        it('renders newsletter content', () => {
            render(
                <NewsletterFeed
                    newsletters={[makeNewsletter({ content: 'Stocks are up today' })]}
                />,
            );
            expect(screen.getByText('Stocks are up today')).toBeInTheDocument();
        });

        it('renders brief count badge for a single newsletter', () => {
            render(<NewsletterFeed newsletters={[makeNewsletter()]} />);
            expect(screen.getByText(/1 Brief$/)).toBeInTheDocument();
        });

        it('renders plural brief count badge for multiple newsletters', () => {
            render(
                <NewsletterFeed
                    newsletters={[makeNewsletter({ id: 'a' }), makeNewsletter({ id: 'b' })]}
                />,
            );
            expect(screen.getByText(/2 Briefs/)).toBeInTheDocument();
        });

        it('renders sender information', () => {
            render(<NewsletterFeed newsletters={[makeNewsletter()]} />);
            expect(screen.getByText('test@example.com')).toBeInTheDocument();
        });

        it('cleans sender email addresses from name badges', () => {
            render(
                <NewsletterFeed
                    newsletters={[
                        makeNewsletter({ sender: 'The Daily Upside <squad@thedailyupside.com>' }),
                    ]}
                />,
            );
            expect(screen.getByText('The Daily Upside')).toBeInTheDocument();
            expect(screen.queryByText(/squad@thedailyupside.com/)).not.toBeInTheDocument();
        });

        it('falls back to original sender when cleaning yields an empty string', () => {
            render(
                <NewsletterFeed
                    newsletters={[makeNewsletter({ sender: '<squad@thedailyupside.com>' })]}
                />,
            );
            expect(screen.getByText('<squad@thedailyupside.com>')).toBeInTheDocument();
        });

        it('does not render the empty-state message when newsletters are present', () => {
            render(<NewsletterFeed newsletters={[makeNewsletter()]} />);
            expect(screen.queryByText('No briefings ingested yet today')).not.toBeInTheDocument();
        });
    });
});
