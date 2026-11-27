import { describe, expect, it } from 'vitest';
import {
    clientIpFrom,
    GUEST_COOKIE_MAX_AGE,
    guestOwnerKey,
    hashCookieValue,
    hashIp,
    signGuestId,
    userOwnerKey,
    verifyGuestCookie,
} from './guest-cookie';

const SECRET = 'test-secret';
const ID = '11111111-2222-4333-8444-555555555555';

describe('guest cookie signing', () => {
    it('round-trips a signed id', () => {
        const raw = signGuestId(ID, SECRET);
        expect(verifyGuestCookie(raw, SECRET)).toBe(ID);
    });

    it('rejects a tampered id', () => {
        const raw = signGuestId(ID, SECRET);
        const forged = raw.replace(ID, '99999999-2222-4333-8444-555555555555');
        expect(verifyGuestCookie(forged, SECRET)).toBeNull();
    });

    it('rejects a signature from another secret', () => {
        expect(verifyGuestCookie(signGuestId(ID, 'other'), SECRET)).toBeNull();
    });

    it('rejects unsigned, truncated and non-uuid values', () => {
        expect(verifyGuestCookie(undefined, SECRET)).toBeNull();
        expect(verifyGuestCookie('', SECRET)).toBeNull();
        expect(verifyGuestCookie('not-a-cookie', SECRET)).toBeNull();
        expect(verifyGuestCookie(`${ID}.`, SECRET)).toBeNull();
        expect(verifyGuestCookie(`${ID}.${'a'.repeat(63)}`, SECRET)).toBeNull();
        expect(verifyGuestCookie(`nope.${'a'.repeat(64)}`, SECRET)).toBeNull();
    });

    it('does not throw on absurd input', () => {
        expect(verifyGuestCookie('x'.repeat(10_000), SECRET)).toBeNull();
    });

    it('keeps a year of cookies', () => {
        expect(GUEST_COOKIE_MAX_AGE).toBeGreaterThan(60 * 60 * 24 * 300);
    });
});

describe('identity keys and hashes', () => {
    it('namespaces owners by tier', () => {
        expect(guestOwnerKey(ID)).toBe(`guest:${ID}`);
        expect(userOwnerKey(ID)).toBe(`user:${ID}`);
    });

    it('hashes the exact cookie value', () => {
        const raw = signGuestId(ID, SECRET);
        expect(hashCookieValue(raw).equals(hashCookieValue(raw))).toBe(true);
        expect(hashCookieValue(raw).equals(hashCookieValue(`${raw}x`))).toBe(false);
    });

    it('normalises ip hashes and tolerates missing ip', () => {
        expect(hashIp(' 1.2.3.4 ')?.equals(hashIp('1.2.3.4') as Buffer)).toBe(true);
        expect(hashIp(null)).toBeNull();
        expect(hashIp('')).toBeNull();
    });
});

describe('client ip trust', () => {
    it('uses CF-Connecting-IP, never X-Forwarded-For', () => {
        const headers = {
            get(name: string) {
                if (name === 'cf-connecting-ip') return '9.9.9.9';
                if (name === 'x-forwarded-for') return '1.2.3.4';
                return null;
            },
        };
        expect(clientIpFrom(headers)).toBe('9.9.9.9');
    });

    it('returns null when Cloudflare did not see the request', () => {
        const headers = {
            get(name: string) {
                return name === 'x-forwarded-for' ? '1.2.3.4' : null;
            },
        };
        expect(clientIpFrom(headers)).toBeNull();
    });
});
