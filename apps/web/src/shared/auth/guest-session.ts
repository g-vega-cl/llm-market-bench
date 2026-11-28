import { randomUUID } from 'node:crypto';
import { getCookies, getRequest, setCookie } from '@tanstack/react-start/server';
import { getDbAdminClient } from '~/lib/db';
import {
    byteaHex,
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
    source: 'cookie' | 'no-cookie' | 'read-failed';
}

/**
 * Read-only sibling of ensureGuestSession: the balance the caller's own cookie
 * has left, without minting anything. Minting on page view would write a
 * session row for every crawler that opens the demo, and the panel only needs
 * to tell a returning visitor how many runs they have left.
 */
export async function readGuestBalance(): Promise<GuestBalance> {
    const grant = GUEST_TOKEN_GRANT;
    try {
        const raw = getCookies()[GUEST_COOKIE];
        if (!verifyGuestCookie(raw, cookieSecret()))
            return { balance: grant, grant, source: 'no-cookie' };

        const db = getDbAdminClient();
        // The balance is keyed on the *session* id, which the mint generates; the
        // uuid inside the cookie is only a signing nonce. Resolve through the
        // token hash, exactly as mint_guest_tokens does, or every guest reads as
        // untouched.
        // token_hash is BYTEA, so the filter needs Postgres's bytea input form;
        // a bare hex string compares as text and silently matches nothing.
        const tokenHash = byteaHex(hashCookieValue(raw as string).toString('hex'));
        const { data: session, error: sessionError } = await db
            .from('guest_sessions')
            .select('id')
            .eq('token_hash', tokenHash)
            .maybeSingle();
        if (sessionError)
            throw new Error(`Could not read the guest session: ${sessionError.message}`);

        // Signed but never minted (nobody has clicked yet): the grant is owed.
        if (!session?.id) return { balance: grant, grant, source: 'cookie' };

        const { data, error } = await db
            .from('token_balances')
            .select('balance')
            .eq('owner_key', guestOwnerKey(session.id as string))
            .maybeSingle();
        if (error) throw new Error(`Could not read the guest balance: ${error.message}`);

        return {
            balance: Number(data?.balance ?? grant),
            grant,
            source: 'cookie',
        };
    } catch (error) {
        // A silent fallback here once made a spent balance look untouched, so
        // say why in the log while still rendering something usable.
        console.error('[guest] balance read failed, falling back to the grant', error);
        return { balance: grant, grant, source: 'read-failed' };
    }
}
