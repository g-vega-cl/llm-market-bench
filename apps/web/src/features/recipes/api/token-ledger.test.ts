import { beforeEach, describe, expect, it, vi } from 'vitest';
import { refundToken, reserveToken, TokenError } from './token-ledger';

const mockRpc = vi.fn();

vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => ({ rpc: mockRpc }),
    getDbServerClient: () => ({ rpc: mockRpc }),
}));

const JOB = '11111111-1111-4111-8111-111111111111';

beforeEach(() => {
    mockRpc.mockReset();
});

describe('reserveToken', () => {
    it('returns the post-spend balance', async () => {
        mockRpc.mockResolvedValue({ data: [{ ok: true, balance: 4, code: 'ok' }], error: null });

        await expect(reserveToken('user:abc', 'backtest', JOB)).resolves.toEqual({ balance: 4 });
        expect(mockRpc).toHaveBeenCalledWith('reserve_token', {
            p_owner: 'user:abc',
            p_kind: 'backtest',
            p_ref: JOB,
        });
    });

    it('treats a retried reserve as success without moving the balance', async () => {
        mockRpc.mockResolvedValue({
            data: [{ ok: true, balance: 2, code: 'already_reserved' }],
            error: null,
        });
        await expect(reserveToken('user:abc', 'backtest', JOB)).resolves.toEqual({ balance: 2 });
    });

    it.each([
        ['no_tokens', 'You are out of tokens. Sign up to get 15 every week.'],
        ['guest_budget', "Today's guest runs are used up. Sign up to keep building."],
        ['refunded', 'That run was already refunded. Start a new one.'],
    ])('surfaces %s as a typed refusal', async (code, message) => {
        mockRpc.mockResolvedValue({ data: [{ ok: false, balance: 0, code }], error: null });

        const error = await reserveToken('guest:abc', 'backtest', JOB).catch((e) => e);
        expect(error).toBeInstanceOf(TokenError);
        expect(error.code).toBe(code);
        expect(error.message).toBe(message);
    });

    it('fails loudly when the RPC itself errors', async () => {
        mockRpc.mockResolvedValue({ data: null, error: { message: 'connection reset' } });
        await expect(reserveToken('user:abc', 'backtest', JOB)).rejects.toThrow('connection reset');
    });

    it('refuses an empty response instead of assuming success', async () => {
        mockRpc.mockResolvedValue({ data: null, error: null });
        await expect(reserveToken('user:abc', 'backtest', JOB)).rejects.toThrow('empty response');
    });
});

describe('refundToken', () => {
    it('reports a refund', async () => {
        mockRpc.mockResolvedValue({ data: [{ refunded: true }], error: null });
        await expect(refundToken(JOB, 'failed')).resolves.toBe(true);
        expect(mockRpc).toHaveBeenCalledWith('settle_token', {
            p_ref: JOB,
            p_outcome: 'failed',
        });
    });

    it('reports an already-settled run as not refunded', async () => {
        mockRpc.mockResolvedValue({ data: [{ refunded: false }], error: null });
        await expect(refundToken(JOB, 'expired')).resolves.toBe(false);
    });
});
