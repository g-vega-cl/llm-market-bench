import { describe, expect, it } from 'vitest';
import { isNyseOpenAt } from './market-hours';

describe('isNyseOpenAt', () => {
    describe('EDT (UTC-4) — 2026-07-15 (Wednesday)', () => {
        it('9:29 AM ET (13:29 UTC) is CLOSED — one minute before open', () => {
            expect(isNyseOpenAt(new Date('2026-07-15T13:29:00Z'))).toBe(false);
        });

        it('9:30 AM ET (13:30 UTC) is OPEN — exact open boundary', () => {
            expect(isNyseOpenAt(new Date('2026-07-15T13:30:00Z'))).toBe(true);
        });

        it('11:00 AM ET (15:00 UTC) is OPEN — mid-session', () => {
            expect(isNyseOpenAt(new Date('2026-07-15T15:00:00Z'))).toBe(true);
        });

        it('3:59 PM ET (19:59 UTC) is OPEN — one minute before close', () => {
            expect(isNyseOpenAt(new Date('2026-07-15T19:59:00Z'))).toBe(true);
        });

        it('4:00 PM ET (20:00 UTC) is CLOSED — exact close boundary', () => {
            expect(isNyseOpenAt(new Date('2026-07-15T20:00:00Z'))).toBe(false);
        });
    });

    describe('EST (UTC-5) — 2026-01-15 (Thursday)', () => {
        it('9:29 AM ET (14:29 UTC) is CLOSED — one minute before open (BUG: old code reported OPEN)', () => {
            expect(isNyseOpenAt(new Date('2026-01-15T14:29:00Z'))).toBe(false);
        });

        it('9:30 AM ET (14:30 UTC) is OPEN — exact open boundary (BUG: old code reported closed at 13:30 UTC instead)', () => {
            expect(isNyseOpenAt(new Date('2026-01-15T14:30:00Z'))).toBe(true);
        });

        it('3:59 PM ET (20:59 UTC) is OPEN — one minute before close (BUG: old code reported CLOSED at 20:00 UTC)', () => {
            expect(isNyseOpenAt(new Date('2026-01-15T20:59:00Z'))).toBe(true);
        });

        it('4:00 PM ET (21:00 UTC) is CLOSED — exact close boundary', () => {
            expect(isNyseOpenAt(new Date('2026-01-15T21:00:00Z'))).toBe(false);
        });
    });

    describe('weekends', () => {
        it('Saturday 10:00 AM ET is CLOSED', () => {
            expect(isNyseOpenAt(new Date('2026-01-17T15:00:00Z'))).toBe(false);
        });

        it('Sunday 10:00 AM ET is CLOSED', () => {
            expect(isNyseOpenAt(new Date('2026-01-18T15:00:00Z'))).toBe(false);
        });
    });
});
