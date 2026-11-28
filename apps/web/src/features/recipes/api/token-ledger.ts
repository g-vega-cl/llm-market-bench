import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';

/**
 * Token ledger calls. Every spend is reserved against the queue row id, so the
 * ledger and the work item share one identifier and a refund can only ever name
 * a run that actually exists.
 */
export type TokenCode = 'no_tokens' | 'guest_budget' | 'refunded' | 'bad_kind' | 'already_reserved';

export class TokenError extends Error {
    readonly code: TokenCode;

    /** `message` overrides the shared copy when the audience changes it. */
    constructor(code: TokenCode, message?: string) {
        super(message ?? TOKEN_MESSAGES[code] ?? 'This run could not be started.');
        this.name = 'TokenError';
        this.code = code;
    }
}

export const TOKEN_MESSAGES: Record<TokenCode, string> = {
    no_tokens: 'You are out of tokens. They refill Monday 09:30 ET.',
    guest_budget: "Today's guest runs are used up. Sign up to keep building.",
    refunded: 'That run was already refunded. Start a new one.',
    bad_kind: 'That is not a token-spendable job.',
    already_reserved: 'That run was already started.',
};

/**
 * A visitor with no account cannot wait for the weekly refill — the only way
 * out is to sign up — so the same refusal code needs different copy.
 */
export function tokenMessage(code: TokenCode, ownerKey: string): string {
    if (code === 'no_tokens' && ownerKey.startsWith('guest:')) {
        return 'You are out of guest tokens. Sign up for 15 a week.';
    }
    return TOKEN_MESSAGES[code] ?? 'This run could not be started.';
}

export interface TokenBalance {
    balance: number;
}

function firstRow(data: unknown): Record<string, unknown> | undefined {
    if (Array.isArray(data)) return data[0] as Record<string, unknown> | undefined;
    if (data && typeof data === 'object') return data as Record<string, unknown>;
    return undefined;
}

export async function reserveToken(
    ownerKey: string,
    kind: 'backtest' | 'live_week',
    ref: string,
): Promise<TokenBalance> {
    const db = getDbAdminClient();
    const { data, error } = await db.rpc('reserve_token', {
        p_owner: ownerKey,
        p_kind: kind,
        p_ref: ref,
    });
    if (error) throw new Error(`Could not reserve a token: ${error.message}`);

    const row = firstRow(data);
    if (!row) throw new Error('Could not reserve a token: empty response');
    if (row.ok !== true) {
        const code = (row.code as TokenCode) ?? 'no_tokens';
        throw new TokenError(code, tokenMessage(code, ownerKey));
    }

    return { balance: Number(row.balance ?? 0) };
}

/**
 * Refusal codes arrive as `TOKEN:<code>` from the RPC; anything else passes
 * through untouched. Pass the owner key so the same code speaks to the right
 * audience — an account is waiting for a refill, a guest is being asked to sign
 * up. Without it, the account copy is assumed.
 */
export function tokenErrorMessage(message: string, ownerKey = 'user:'): string {
    const match = /^TOKEN:([a-z_]+)$/.exec(message.trim());
    if (!match) return message;
    const code = match[1] as TokenCode;
    if (!(code in TOKEN_MESSAGES)) return message;
    return tokenMessage(code, ownerKey);
}

/** Refunds a failed or timed-out backtest. Idempotent: a second call is a no-op. */
export async function refundToken(ref: string, outcome: 'failed' | 'expired'): Promise<boolean> {
    const db = getDbAdminClient();
    const { data, error } = await db.rpc('settle_token', { p_ref: ref, p_outcome: outcome });
    if (error) throw new Error(`Could not refund a token: ${error.message}`);
    const row = firstRow(data);
    return row?.refunded === true;
}

/**
 * Refills the signed-in owner for the current ET week. The archive DB holds no
 * auth users (Supabase Cloud owns auth), so there is no user list to cron over:
 * each authenticated load tops itself up, and the RPC is idempotent per week.
 */
export const ensureWeeklyTokensFn = createServerFn({ method: 'POST' }).handler(async () => {
    const auth = getAuthServerClient();
    const {
        data: { user },
    } = await auth.auth.getUser();
    if (!user?.id) return null;

    const db = getDbAdminClient();
    const { data, error } = await db.rpc('refill_this_week', {
        p_owner: `user:${user.id}`,
        p_amount: 15,
    });
    if (error) throw new Error(`Could not refill tokens: ${error.message}`);

    const row = firstRow(data);
    return { balance: Number(row?.balance ?? 0), applied: row?.applied === true };
});
