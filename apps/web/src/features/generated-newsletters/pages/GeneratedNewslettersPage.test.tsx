import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { FormattedGeneratedNewsletter } from '../api/fetch-generated-newsletters';
import { GeneratedNewslettersPage } from './GeneratedNewslettersPage';

vi.mock('@tanstack/react-router', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: test mock
    Link: ({ children, to }: any) => <a href={to}>{children}</a>,
}));

const mockNewsletters: FormattedGeneratedNewsletter[] = [
    {
        id: 'gn-1',
        title: 'Morning Market Pulse: Tech Surge & Fed Signals',
        summary: 'Tech stocks rally on AI hardware momentum while Fed signals rate stability.',
        content: 'Markets opened on a bullish footing today, propelled by massive momentum.',
        bullet_points: ['NVIDIA & AMD hit fresh highs', 'Fed signals rate stability'],
        session: 'open',
        read_time_minutes: 2,
        source_count: 3,
        formatted_time: '09:00 ET',
        created_at: '2026-08-06T09:00:00Z',
        formattedDate: 'August 6, 2026',
        displayTime: '09:00 ET',
    },
    {
        id: 'gn-2',
        title: 'Evening Market Close: Late Session Reversal',
        summary: 'Markets closed slightly lower following afternoon profit taking.',
        content: 'The afternoon session saw mild consolidation across broad indexes.',
        bullet_points: ['Profit taking in mega-cap tech', 'Yields remain flat'],
        session: 'close',
        read_time_minutes: 2,
        source_count: 4,
        formatted_time: '17:00 ET',
        created_at: '2026-08-06T17:00:00Z',
        formattedDate: 'August 6, 2026',
        displayTime: '17:00 ET',
    },
];

describe('GeneratedNewslettersPage', () => {
    it('renders heading and empty state when no newsletters are provided', () => {
        render(<GeneratedNewslettersPage initialNewsletters={[]} />);
        expect(screen.getByText('Daily Market Intelligence Briefings')).toBeInTheDocument();
        expect(screen.getByText('No generated newsletters available yet')).toBeInTheDocument();
    });

    it('renders newsletter title, executive summary, and formatted time', () => {
        render(<GeneratedNewslettersPage initialNewsletters={mockNewsletters} />);
        expect(screen.getByText('Daily Market Intelligence Briefings')).toBeInTheDocument();
        expect(
            screen.getAllByText('Morning Market Pulse: Tech Surge & Fed Signals')[0],
        ).toBeInTheDocument();
        expect(
            screen.getAllByText(
                'Tech stocks rally on AI hardware momentum while Fed signals rate stability.',
            )[0],
        ).toBeInTheDocument();
        expect(screen.getByText('🕒 Created at 09:00 ET')).toBeInTheDocument();
        expect(screen.getAllByText('⏱️ 2 min read')[0]).toBeInTheDocument();
    });

    it('renders bullet point key takeaways', () => {
        render(<GeneratedNewslettersPage initialNewsletters={mockNewsletters} />);
        expect(screen.getByText('NVIDIA & AMD hit fresh highs')).toBeInTheDocument();
        expect(screen.getByText('Fed signals rate stability')).toBeInTheDocument();
    });
});
