import { describe, expect, it } from 'vitest';
import {
    canActivateTurboEt,
    computeTurboExpiryIso,
    formatTurboRemainingLabel,
    getEtDateString,
    getNextLiveSlotLabel,
    isKnownUsMarketHolidayEt,
    isRegularMarketHoursEt,
    isTurboActive,
} from './market-hours';

describe('market-hours', () => {
    it('detects regular US market hours and excludes weekends and holidays including Good Friday', () => {
        expect(isRegularMarketHoursEt(new Date('2026-11-18T09:30:00-05:00'))).toBe(true);
        expect(isRegularMarketHoursEt(new Date('2026-11-18T15:59:00-05:00'))).toBe(true);
        expect(isRegularMarketHoursEt(new Date('2026-11-18T09:29:00-05:00'))).toBe(false);
        expect(isRegularMarketHoursEt(new Date('2026-11-18T16:00:00-05:00'))).toBe(false);
        expect(isRegularMarketHoursEt(new Date('2026-11-21T11:00:00-05:00'))).toBe(false); // Sat
        expect(isRegularMarketHoursEt(new Date('2026-11-26T11:00:00-05:00'))).toBe(false); // Thanksgiving
        expect(isRegularMarketHoursEt(new Date('2026-04-03T11:00:00-04:00'))).toBe(false); // Good Friday
        expect(isKnownUsMarketHolidayEt('2026-11-26')).toBe(true);
        expect(isKnownUsMarketHolidayEt('2026-04-03')).toBe(true);
        expect(isKnownUsMarketHolidayEt('2026-11-20')).toBe(false);
        expect(getEtDateString(new Date('2026-11-20T23:30:00-05:00'))).toBe('2026-11-20');

        expect(canActivateTurboEt(new Date('2026-11-18T15:54:00-05:00'))).toBe(true);
        expect(canActivateTurboEt(new Date('2026-11-18T15:55:00-05:00'))).toBe(false);
    });

    it('caps Turbo expiry at 16:00 ET close across both EST and EDT', () => {
        // 11:15 EST -> 12:15 EST
        expect(computeTurboExpiryIso(new Date('2026-11-18T11:15:00-05:00'))).toBe(
            new Date('2026-11-18T12:15:00-05:00').toISOString(),
        );
        // 15:25 EST -> capped at 16:00 EST
        expect(computeTurboExpiryIso(new Date('2026-11-18T15:25:00-05:00'))).toBe(
            new Date('2026-11-18T16:00:00-05:00').toISOString(),
        );
        // 15:30 EDT (summer) -> capped at 16:00 EDT
        expect(computeTurboExpiryIso(new Date('2026-06-10T15:30:00-04:00'))).toBe(
            new Date('2026-06-10T16:00:00-04:00').toISOString(),
        );
    });

    it('computes active Turbo state and remaining minutes label', () => {
        const now = new Date('2026-11-18T11:00:00-05:00');
        const expiresAt = new Date('2026-11-18T11:42:00-05:00').toISOString();
        expect(isTurboActive(expiresAt, now)).toBe(true);
        expect(formatTurboRemainingLabel(expiresAt, now)).toBe('42m left');
        expect(isTurboActive(expiresAt, new Date('2026-11-18T11:43:00-05:00'))).toBe(false);
        expect(
            formatTurboRemainingLabel(expiresAt, new Date('2026-11-18T16:05:00-05:00')),
        ).toBeNull();
    });

    it('formats 30-minute next live slot labels in ET', () => {
        expect(getNextLiveSlotLabel(new Date('2026-11-18T12:00:00-05:00'))).toBe('12:30 ET today');
        expect(getNextLiveSlotLabel(new Date('2026-11-18T15:50:00-05:00'))).toBe('16:00 ET today');
        expect(getNextLiveSlotLabel(new Date('2026-11-18T16:05:00-05:00'))).toBe(
            '09:30 ET tomorrow',
        );
        expect(getNextLiveSlotLabel(new Date('2026-11-20T16:05:00-05:00'))).toBe('09:30 ET Monday');
        expect(getNextLiveSlotLabel(new Date('2026-11-21T11:00:00-05:00'))).toBe('09:30 ET Monday');
    });
});
