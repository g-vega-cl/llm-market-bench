import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { parseScenarioPercentages } from '~/lib/parse-scenario-percentages';
import { FutureCatalysts } from './FutureCatalysts';

describe('FutureCatalysts Component', () => {
    it('renders Critical badge when importance_score is 9', () => {
        const events = [
            {
                id: 'evt-1',
                content:
                    '[CALENDAR EVENT] (12:30 PM) 2026-09-11: US CPI Print: Inflation report | Impact: BEARISH | Date: 2026-09-11',
                created_at: '2026-09-02T12:00:00Z',
                memory_type: 'CALENDAR_EVENT',
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: 1.0,
                importance_score: 9,
                target_date: '2026-09-11',
                metadata: {
                    is_calendar_event: true,
                    is_future_catalyst: true,
                    event_time: '12:30 PM',
                },
            },
        ];

        render(<FutureCatalysts events={events} />);

        expect(screen.getByText('Critical')).toBeInTheDocument();
        expect(screen.getByText(/US CPI Print/)).toBeInTheDocument();
        expect(screen.getAllByText(/12:30 PM/).length).toBeGreaterThanOrEqual(1);
    });

    it('renders High badge when importance_score is 8', () => {
        const events = [
            {
                id: 'evt-2',
                content:
                    '[CALENDAR EVENT] (01:30 AM) 2026-09-03: Australia GDP: Strong growth | Impact: BULLISH | Date: 2026-09-03',
                created_at: '2026-09-02T12:00:00Z',
                memory_type: 'CALENDAR_EVENT',
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: 1.0,
                importance_score: 8,
                target_date: '2026-09-03',
                metadata: {
                    is_calendar_event: true,
                    is_future_catalyst: true,
                    event_time: '01:30 AM',
                },
            },
        ];

        render(<FutureCatalysts events={events} />);

        expect(screen.getByText('High')).toBeInTheDocument();
    });
});

describe('parseScenarioPercentages', () => {
    it('extracts basic percentage (40%)', () => {
        const result = parseScenarioPercentages('Market drops 40% in the bear case');
        expect(result).toHaveLength(1);
        expect(result[0].percentage).toBe('40%');
        expect(result[0].text).toBe('Market drops 40% in the bear case');
    });

    it('extracts percentage with space (40 %)', () => {
        const result = parseScenarioPercentages('Probability is 40 % for this outcome');
        expect(result[0].percentage).toBe('40%');
    });

    it('extracts percentage in parentheses (80%)', () => {
        const result = parseScenarioPercentages('high chance (80%) for bullish case');
        expect(result[0].percentage).toBe('80%');
    });

    it('returns null for lines without percentages', () => {
        const result = parseScenarioPercentages('Bullish scenario with strong momentum');
        expect(result[0].percentage).toBeNull();
    });

    it('handles multiple lines with mixed percentages', () => {
        const input =
            'Bull case: 70% probability\nBear case: 30% probability\nNeutral: steady growth';
        const result = parseScenarioPercentages(input);

        expect(result).toHaveLength(3);
        expect(result[0].percentage).toBe('70%');
        expect(result[1].percentage).toBe('30%');
        expect(result[2].percentage).toBeNull();
    });

    it('handles triple-digit percentages (100%)', () => {
        const result = parseScenarioPercentages('Full allocation at 100%');
        expect(result[0].percentage).toBe('100%');
    });

    it('handles empty string', () => {
        const result = parseScenarioPercentages('');
        expect(result).toHaveLength(1);
        expect(result[0].text).toBe('');
        expect(result[0].percentage).toBeNull();
    });

    it('extracts only first percentage if multiple on same line', () => {
        const result = parseScenarioPercentages('Range is 50% to 80% likely');
        expect(result[0].percentage).toBe('50%');
    });

    it('splits scenarios without newlines using Scenario A style pattern', () => {
        const input =
            'Scenario A: Bullish case (70%) - price goes up. Scenario B: Bearish case (30%) - price goes down.';
        const result = parseScenarioPercentages(input);

        expect(result).toHaveLength(2);
        expect(result[0].percentage).toBe('70%');
        expect(result[0].text).toBe('Scenario A: Bullish case (70%) - price goes up.');
        expect(result[1].percentage).toBe('30%');
        expect(result[1].text).toBe('Scenario B: Bearish case (30%) - price goes down.');
    });
});
