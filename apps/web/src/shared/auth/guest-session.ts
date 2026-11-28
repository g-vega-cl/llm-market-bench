import { randomUUID } from 'node:crypto';
import { getCookies, getRequest, setCookie } from '@tanstack/react-start/server';
import { getDbAdminClient } from '~/lib/db';
import {
    clientIpFrom,
    GUEST_COOKIE,
    GUEST_COOKIE_MAX_AGE,
    GUEST_TOKEN_GRANT,
    guestOwnerKey,
    hashCookieValue,
    hashIp,
    signGuestId,
    verifyGuestCookie,
} from './guest-cookie';

export interface GuestSession {
    guestId: string;
    ownerKey: string;
    balance: number;
    isNew: boolean;
}

/**
 * The signing key doubles as the database credential boundary: both are
 * server-only. GUEST_COOKIE_SECRET wins when set, otherwise the archive service
 * role key is used so a deploy cannot forget a new variable and ship an
 * unsigned cookie.
 */
function cookieSecret(): string {
    const secret =
        process.env.GUEST_COOKIE_SECRET ||
        process.env.ARCHIVE_DB_SERVICE_ROLE_KEY ||
        process.env.SUPABASE_SERVICE_ROLE_KEY;
    if (!secret) throw new Error('Missing guest cookie secret');
    return secret;
}

function clientIpHash(): string | null {
    try {
        return hashIp(clientIpFrom(getRequest().headers))?.toString('hex') ?? null;
    } catch {
        // Outside a request context (unit tests, background callers).
        return null;
    }
}

/**
 * Reads the guest cookie, minting one when absent or invalid, and resolves the
 * guest's token balance. Never throws for a missing cookie; throws only when the
 * database cannot be reached, because a silent zero balance would look like an
 * exhausted user.
 */
export async function ensureGuestSession(): Promise<GuestSession> {
    const secret = cookieSecret();
    const cookies = getCookies();
    const raw = cookies[GUEST_COOKIE];
    const verified = verifyGuestCookie(raw, secret);

    const cookieValue = verified ? (raw as string) : signGuestId(randomUUID(), secret);
    const guestId = verified ?? verifyGuestCookie(cookieValue, secret);
    if (!guestId) throw new Error('Guest cookie could not be signed');

    if (!verified) {
        setCookie(GUEST_COOKIE, cookieValue, {
            httpOnly: true,
            sameSite: 'lax',
            secure: true,
            path: '/',
            maxAge: GUEST_COOKIE_MAX_AGE,
        });
    }

    const db = getDbAdminClient();
    const { data, error } = await db.rpc('mint_guest_tokens', {
        p_token_hash: hashCookieValue(cookieValue).toString('hex'),
        p_ip_hash: clientIpHash(),
    });

    if (error) throw new Error(`Could not resolve guest session: ${error.message}`);

    const row = Array.isArray(data) ? data[0] : data;
    if (!row?.guest_id) throw new Error('Guest mint returned no identity');

    return {
        guestId: row.guest_id as string,
        ownerKey: guestOwnerKey(row.guest_id as string),
        balance: Number(row.balance ?? 0),
        isNew: Boolean(row.created),
    };
}

export { GUEST_TOKEN_GRANT };

export interface GuestBalance {
    balance: number;
    grant: number;
}

/**
 * Read-only sibling of ensureGuestSession: the balance the caller's own cookie
 * has left, without minting anything. Minting on page view would write a
 * session row for every crawler that opens the demo, and the panel only needs
 * to tell a returning visitor how many runs they have left.
 */
export async function readGuestBalance(): Promise<GuestBalance> {
    try {
        const guestId = verifyGuestCookie(getCookies()[GUEST_COOKIE], cookieSecret());
        if (!guestId) return { balance: GUEST_TOKEN_GRANT, grant: GUEST_TOKEN_GRANT };

        const db = getDbAdminClient();
        const { data, error } = await db
            .from('token_balances')
            .select('balance')
            .eq('owner_key', guestOwnerKey(guestId))
            .maybeSingle();
        if (error) throw new Error(`Could not read the guest balance: ${error.message}`);

        // A signed cookie with no row means the mint never ran; the grant is
        // still owed, so show it rather than a zero the visitor cannot spend.
        return {
            balance: Number(data?.balance ?? GUEST_TOKEN_GRANT),
            grant: GUEST_TOKEN_GRANT,
        };
    } catch {
        // Unreachable or unconfigured: the click path is the authority and will
        // refuse with a real message, so do not block the page on this.
        return { balance: GUEST_TOKEN_GRANT, grant: GUEST_TOKEN_GRANT };
    }
}
