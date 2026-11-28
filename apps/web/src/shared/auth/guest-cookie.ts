import { createHash, createHmac, timingSafeEqual } from 'node:crypto';

/**
 * Signed guest identity for logged-out visitors.
 *
 * The cookie is the only thing that names a guest. It is a random UUID plus an
 * HMAC of that UUID, so the server can verify a guest without a database read
 * and a visitor cannot forge someone else's balance by editing the value.
 *
 * Pure functions only: the request/cookie glue lives in `guest-session.ts` so
 * this module stays testable without a server runtime.
 */
export const GUEST_COOKIE = 'bfy_guest';
export const GUEST_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
export const GUEST_TOKEN_GRANT = 5;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function sign(id: string, secret: string): string {
    return createHmac('sha256', secret).update(id).digest('hex');
}

export function signGuestId(id: string, secret: string): string {
    if (!UUID_RE.test(id)) throw new Error(`guest id is not a uuid: ${id}`);
    return `${id}.${sign(id, secret)}`;
}

/** Returns the guest id, or null for anything unsigned, truncated or tampered. */
export function verifyGuestCookie(raw: string | undefined, secret: string): string | null {
    if (!raw) return null;
    const at = raw.lastIndexOf('.');
    if (at <= 0) return null;

    const id = raw.slice(0, at);
    const provided = raw.slice(at + 1);
    if (!UUID_RE.test(id) || !/^[0-9a-f]{64}$/i.test(provided)) return null;

    const expected = sign(id, secret);
    const a = Buffer.from(expected, 'hex');
    const b = Buffer.from(provided.toLowerCase(), 'hex');
    if (a.length !== b.length) return null;
    return timingSafeEqual(a, b) ? id : null;
}

/** Hash of the exact cookie value, so the stored hash dies with the cookie. */
export function hashCookieValue(raw: string): Buffer {
    return createHash('sha256').update(raw).digest();
}

export function hashIp(ip: string | null | undefined): Buffer | null {
    if (!ip) return null;
    const normalized = ip.trim().toLowerCase();
    if (!normalized) return null;
    return createHash('sha256').update(normalized).digest();
}

/**
 * Cloudflare sets CF-Connecting-IP and strips any client copy. nginx appends
 * X-Forwarded-For, so the leftmost value there is attacker-controlled and must
 * never be used as an identity key.
 */
export function clientIpFrom(headers: { get(name: string): string | null }): string | null {
    const cf = headers.get('cf-connecting-ip')?.trim();
    return cf || null;
}

export function guestOwnerKey(id: string): string {
    return `guest:${id}`;
}

export function userOwnerKey(id: string): string {
    return `user:${id}`;
}

/**
 * Postgres bytea literal for a hex digest.
 *
 * PostgREST filters compare a BYTEA column against Postgres's bytea input
 * syntax, so a bare hex string is compared as text and matches nothing — a
 * silent empty result, not an error. Built from a char code so this file
 * contains no backslash literal to miscount.
 */
export function byteaHex(hex: string): string {
    return `${String.fromCharCode(92)}x${hex}`;
}
