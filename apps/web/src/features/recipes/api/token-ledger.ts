import { getDbAdminClient } from '~/lib/db';

/**
 * Token ledger calls. Every spend is reserved against the queue row id, so the
 * ledger and the work item share one identifier and a refund can only ever name
 * a run that actually exists.
 */
export type TokenCode = 'no_tokens' | 'guest_budget' | 'refunded' | 'bad_kind' | 'already_reserved';

export class TokenError extends Error {
    readonly code: TokenCode;

    constructor(code: TokenCode) {
        super(TOKEN_MESSAGES[code] ?? 'This run could not be started.');
        this.name = 'TokenError';
        this.code = code;
    }
}

export const TOKEN_MESSAGES: Record<TokenCode, string> = {
    no_tokens: 'You are out of tokens. Sign up to get 15 every week.',
    guest_budget: "Today's guest runs are used up. Sign up to keep building.",
    refunded: 'That run was already refunded. Start a new one.',
    bad_kind: 'That is not a token-spendable job.',
    already_reserved: 'That run was already started.',
};

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
    if (row.ok !== true) throw new TokenError((row.code as TokenCode) ?? 'no_tokens');

    return { balance: Number(row.balance ?? 0) };
}

/** Refusal codes arrive as `TOKEN:<code>` from the RPC; anything else passes through. */
export function tokenErrorMessage(message: string): string {
    const match = /^TOKEN:([a-z_]+)$/.exec(message.trim());
    if (!match) return message;
    const code = match[1] as TokenCode;
    return TOKEN_MESSAGES[code] ?? message;
}

/** Refunds a failed or timed-out backtest. Idempotent: a second call is a no-op. */
export async function refundToken(ref: string, outcome: 'failed' | 'expired'): Promise<boolean> {
    const db = getDbAdminClient();
    const { data, error } = await db.rpc('settle_token', { p_ref: ref, p_outcome: outcome });
    if (error) throw new Error(`Could not refund a token: ${error.message}`);
    const row = firstRow(data);
    return row?.refunded === true;
}
