import { beforeEach, describe, expect, it, vi } from 'vitest';
import { byteaHex, hashCookieValue, signGuestId } from './guest-cookie';

const SECRET = 'test-secret';
const COOKIE_UUID = '11111111-1111-1111-1111-111111111111';
const SESSION_UUID = '22222222-2222-2222-2222-222222222222';

let cookies: Record<string, string> = {};
vi.mock('@tanstack/react-start/server', () => ({
    getCookies: () => cookies,
    getRequest: () => ({ headers: new Headers() }),
    setCookie: () => {},
}));

type Row = { data: unknown; error: unknown };
let sessionLookup: Row = { data: null, error: null };
let balanceLookup: Row = { data: null, error: null };

vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => ({
        from: (table: string) => ({
            select: () => ({
                eq: (_column: string, value: string) => ({
                    maybeSingle: async () => {
                        if (table === 'guest_sessions') {
                            // The lookup must be keyed on the cookie hash, not on
                            // the uuid the cookie carries.
                            const expected = byteaHex(
                                hashCookieValue(cookies.bfy_guest).toString('hex'),
                            );
                            return value === expected ? sessionLookup : { data: null, error: null };
                        }
                        return value === `guest:${SESSION_UUID}`
                            ? balanceLookup
                            : { data: null, error: null };
                    },
                }),
            }),
        }),
    }),
}));

const { readGuestBalance } = await import('./guest-session');

beforeEach(() => {
    process.env.GUEST_COOKIE_SECRET = SECRET;
    cookies = { bfy_guest: signGuestId(COOKIE_UUID, SECRET) };
    sessionLookup = { data: { id: SESSION_UUID }, error: null };
    balanceLookup = { data: { balance: 4 }, error: null };
});

describe('readGuestBalance', () => {
    it('reads the balance through the session row, not the cookie uuid', async () => {
        expect(await readGuestBalance()).toEqual({ balance: 4, grant: 5, source: 'cookie' });
    });

    it('reports the full grant for a visitor who has not minted yet', async () => {
        sessionLookup = { data: null, error: null };
        expect(await readGuestBalance()).toEqual({ balance: 5, grant: 5, source: 'cookie' });
    });

    it('reports the grant when there is no signed cookie', async () => {
        cookies = {};
        expect(await readGuestBalance()).toEqual({ balance: 5, grant: 5, source: 'no-cookie' });
    });

    it('rejects a cookie signed with another secret instead of trusting its uuid', async () => {
        cookies = { bfy_guest: signGuestId(COOKIE_UUID, 'someone-elses-secret') };
        expect(await readGuestBalance()).toEqual({ balance: 5, grant: 5, source: 'no-cookie' });
    });

    it('says so in the log when the read fails, and still renders a balance', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        sessionLookup = { data: null, error: { message: 'db down' } };

        expect(await readGuestBalance()).toEqual({ balance: 5, grant: 5, source: 'read-failed' });
        expect(consoleError).toHaveBeenCalled();
        consoleError.mockRestore();
    });
});

describe('byteaHex', () => {
    it('produces Postgres bytea input syntax, not a bare hex string', () => {
        const literal = byteaHex('ab12');
        expect(literal.charCodeAt(0)).toBe(92); // backslash
        expect(literal.slice(1)).toBe('xab12');
        expect(literal).not.toBe('ab12');
    });
});
