import { describe, expect, it } from 'vitest';
import { ATMOSPHERE_PHASES, resolveAtmospherePhase } from './atmosphere';

describe('resolveAtmospherePhase', () => {
    it('exports all four canonical atmosphere phases', () => {
        expect(ATMOSPHERE_PHASES).toEqual(['dawn', 'daylight', 'dusk', 'after-hours']);
    });

    describe('market-et mode (default, America/New_York)', () => {
        // 2026-01-15 is EST (UTC-5)
        it('returns dawn during pre-market (04:00–09:29 ET)', () => {
            expect(resolveAtmospherePhase(new Date('2026-01-15T09:00:00Z'))).toBe('dawn'); // 04:00 EST
            expect(resolveAtmospherePhase(new Date('2026-01-15T14:29:00Z'))).toBe('dawn'); // 09:29 EST
        });

        it('returns daylight during regular session (09:30–15:59 ET)', () => {
            expect(resolveAtmospherePhase(new Date('2026-01-15T14:30:00Z'))).toBe('daylight'); // 09:30 EST
            expect(resolveAtmospherePhase(new Date('2026-01-15T20:59:00Z'))).toBe('daylight'); // 15:59 EST
        });

        it('returns dusk during close and golden-hour twilight (16:00–19:59 ET)', () => {
            expect(resolveAtmospherePhase(new Date('2026-01-15T21:00:00Z'))).toBe('dusk'); // 16:00 EST
            expect(resolveAtmospherePhase(new Date('2026-01-16T00:59:00Z'))).toBe('dusk'); // 19:59 EST
        });

        it('returns after-hours overnight (20:00–03:59 ET)', () => {
            expect(resolveAtmospherePhase(new Date('2026-01-16T01:00:00Z'))).toBe('after-hours'); // 20:00 EST
            expect(resolveAtmospherePhase(new Date('2026-01-16T08:59:00Z'))).toBe('after-hours'); // 03:59 EST
        });

        // 2026-07-15 is EDT (UTC-4)
        it('respects Eastern Daylight Time (EDT) transitions', () => {
            expect(resolveAtmospherePhase(new Date('2026-07-15T13:29:00Z'))).toBe('dawn'); // 09:29 EDT
            expect(resolveAtmospherePhase(new Date('2026-07-15T13:30:00Z'))).toBe('daylight'); // 09:30 EDT
            expect(resolveAtmospherePhase(new Date('2026-07-15T20:00:00Z'))).toBe('dusk'); // 16:00 EDT
            expect(resolveAtmospherePhase(new Date('2026-07-16T00:00:00Z'))).toBe('after-hours'); // 20:00 EDT
        });
    });

    describe('local mode (visitor timezone)', () => {
        it('resolves phases using local clock boundaries', () => {
            const atLocal = (h: number, m = 0) => new Date(2026, 5, 15, h, m, 0);
            expect(resolveAtmospherePhase(atLocal(5, 0), 'local')).toBe('dawn');
            expect(resolveAtmospherePhase(atLocal(8, 59), 'local')).toBe('dawn');
            expect(resolveAtmospherePhase(atLocal(9, 0), 'local')).toBe('daylight');
            expect(resolveAtmospherePhase(atLocal(16, 59), 'local')).toBe('daylight');
            expect(resolveAtmospherePhase(atLocal(17, 0), 'local')).toBe('dusk');
            expect(resolveAtmospherePhase(atLocal(20, 59), 'local')).toBe('dusk');
            expect(resolveAtmospherePhase(atLocal(21, 0), 'local')).toBe('after-hours');
            expect(resolveAtmospherePhase(atLocal(4, 59), 'local')).toBe('after-hours');
        });
    });

    it('falls back deterministically to dusk on invalid Date values in both modes', () => {
        expect(resolveAtmospherePhase(new Date(Number.NaN), 'market-et')).toBe('dusk');
        expect(resolveAtmospherePhase(new Date(Number.NaN), 'local')).toBe('dusk');
    });
});
