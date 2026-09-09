import { describe, expect, it } from 'vitest';
import {
    type Concept,
    calculateDateOffset,
    cleanCatalystTitle,
    cosineSimilarity,
    mapCatalystsToConcepts,
    parseVector,
} from './fetch-concepts';

describe('fetch-concepts utilities', () => {
    describe('calculateDateOffset', () => {
        const refDate = new Date('2026-09-09T12:00:00Z');

        it('calculates upcoming relative dates', () => {
            const oneWeek = calculateDateOffset('2026-09-16', refDate);
            expect(oneWeek.deltaDays).toBe(7);
            expect(oneWeek.stage).toBe('upcoming');
            expect(oneWeek.label).toBe('1 week from now');

            const twoWeeks = calculateDateOffset('2026-09-23', refDate);
            expect(twoWeeks.deltaDays).toBe(14);
            expect(twoWeeks.stage).toBe('upcoming');
            expect(twoWeeks.label).toBe('2 weeks from now');

            const tomorrow = calculateDateOffset('2026-09-10', refDate);
            expect(tomorrow.deltaDays).toBe(1);
            expect(tomorrow.stage).toBe('upcoming');
            expect(tomorrow.label).toBe('tomorrow');

            const inThreeDays = calculateDateOffset('2026-09-12', refDate);
            expect(inThreeDays.deltaDays).toBe(3);
            expect(inThreeDays.stage).toBe('upcoming');
            expect(inThreeDays.label).toBe('in 3 days');
        });

        it('calculates active/today dates', () => {
            const today = calculateDateOffset('2026-09-09', refDate);
            expect(today.deltaDays).toBe(0);
            expect(today.stage).toBe('active');
            expect(today.label).toBe('today');
        });

        it('calculates digestion stages for events within 3 days past', () => {
            const oneDayAgo = calculateDateOffset('2026-09-08', refDate);
            expect(oneDayAgo.deltaDays).toBe(-1);
            expect(oneDayAgo.stage).toBe('digesting');
            expect(oneDayAgo.label).toBe('digesting, 1 day ago');

            const threeDaysAgo = calculateDateOffset('2026-09-06', refDate);
            expect(threeDaysAgo.deltaDays).toBe(-3);
            expect(threeDaysAgo.stage).toBe('digesting');
            expect(threeDaysAgo.label).toBe('digesting, 3 days ago');
        });

        it('marks events beyond 3 days past as expired', () => {
            const expired = calculateDateOffset('2026-09-05', refDate);
            expect(expired.stage).toBe('expired');
        });
    });

    describe('cosineSimilarity', () => {
        it('calculates exact similarity for identical and orthogonal vectors', () => {
            expect(cosineSimilarity([1, 0], [1, 0])).toBeCloseTo(1.0);
            expect(cosineSimilarity([1, 0], [0, 1])).toBeCloseTo(0.0);
            expect(cosineSimilarity([1, 1], [1, 1])).toBeCloseTo(1.0);
        });

        it('returns 0 for mismatched lengths or empty vectors', () => {
            expect(cosineSimilarity([1, 0], [1, 0, 0])).toBe(0);
            expect(cosineSimilarity([], [])).toBe(0);
        });
    });

    describe('cleanCatalystTitle', () => {
        it('strips calendar event markers and timestamps', () => {
            expect(
                cleanCatalystTitle(
                    '[CALENDAR EVENT] (8:30 AM) US CPI Inflation Print | Impact: BEARISH',
                ),
            ).toBe('US CPI Inflation Print');
            expect(
                cleanCatalystTitle('2026-09-11: Oracle Earnings Cloud Guidance | Impact: HIGH'),
            ).toBe('Oracle Earnings Cloud Guidance');
        });
    });

    describe('parseVector', () => {
        it('handles array and json string vectors', () => {
            expect(parseVector([0.1, 0.2])).toEqual([0.1, 0.2]);
            expect(parseVector('[0.1, 0.2]')).toEqual([0.1, 0.2]);
            expect(parseVector(null)).toBeNull();
            expect(parseVector('invalid-json')).toBeNull();
        });
    });

    describe('mapCatalystsToConcepts', () => {
        it('attaches pre-computed radar rows to concepts with accurate dates', () => {
            const concepts: Concept[] = [
                {
                    id: 'c1',
                    concept_name: 'Semiconductor Capex',
                    mention_count: 5,
                    velocity_score: 2.5,
                    first_mention_at: '2026-09-01',
                    last_mention_at: '2026-09-09',
                    pca_x: 0.1,
                    pca_y: 0.2,
                },
                {
                    id: 'c2',
                    concept_name: 'Regional Banking',
                    mention_count: 3,
                    velocity_score: 0.8,
                    first_mention_at: '2026-09-01',
                    last_mention_at: '2026-09-09',
                    pca_x: -0.1,
                    pca_y: -0.2,
                },
            ];

            const radarRows = [
                {
                    concept_id: 'c1',
                    catalyst_id: 'm1',
                    catalyst_title: 'TSMC Monthly Revenue Report',
                    target_date: '2026-09-10',
                    impact: 'BULLISH',
                    similarity: 0.75,
                    memory_content: 'TSMC Monthly Revenue Report release',
                    related_tickers: ['TSM', 'NVDA'],
                },
            ];

            const refDate = new Date('2026-09-09T12:00:00Z');
            mapCatalystsToConcepts(concepts, radarRows, refDate);

            expect(concepts[0].catalyst).toBeDefined();
            expect(concepts[0].catalyst?.catalyst_title).toBe('TSMC Monthly Revenue Report');
            expect(concepts[0].catalyst?.stage).toBe('upcoming');
            expect(concepts[0].catalyst?.date_offset_label).toBe('tomorrow');
            expect(concepts[0].catalyst?.days_to_event).toBe(1);
            expect(concepts[0].catalyst?.related_tickers).toEqual(['TSM', 'NVDA']);

            expect(concepts[1].catalyst).toBeUndefined();
        });
    });
});
