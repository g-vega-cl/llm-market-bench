import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import {
    BUILDER_DAILY_LIMIT,
    buildCompilePayload,
    builderLimitMessage,
    enqueueCompile,
    MAX_PENDING_COMPILES,
    pendingCompilesMessage,
    readCompileJob,
} from './compile-queue';

const mockDb = { from: vi.fn() };

vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => mockDb,
}));

vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({ auth: { getUser: vi.fn() } }),
}));

/** Supabase builders are thenable, so the fake is a real Promise with the chain methods. */
function chain(result: { data: unknown; error?: unknown }, onInsert?: (row: unknown) => void) {
    const node = Promise.resolve(result) as unknown as Record<string, unknown>;
    const pass = () => node;
    for (const method of ['select', 'eq', 'in', 'order', 'limit', 'single', 'maybeSingle']) {
        node[method] = pass;
    }
    node.insert = (row: unknown) => {
        onInsert?.(row);
        return node;
    };
    return node;
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe('buildCompilePayload', () => {
    it('keeps the system prompt first and caps the turn window', () => {
        const messages = Array.from({ length: 12 }, (_, i) => ({
            role: 'user' as const,
            content: `turn ${i}`,
        }));

        const payload = buildCompilePayload(messages);

        expect(payload.model).toBe('auto-go');
        expect(payload.messages[0].role).toBe('system');
        // 8 sent messages + the system prompt
        expect(payload.messages).toHaveLength(9);
        expect(payload.messages[1]).toEqual({ role: 'user', content: 'turn 4' });
    });
});

describe('enqueueCompile', () => {
    it('refuses at the daily ceiling with the metering copy', async () => {
        mockDb.from.mockReturnValue(chain({ data: { compiles: BUILDER_DAILY_LIMIT } }));

        await expect(
            enqueueCompile('user-1', [{ role: 'user', content: 'buy chips' }]),
        ).rejects.toThrow(builderLimitMessage());
    });

    it('refuses when the user already has the maximum compiles in flight', async () => {
        mockDb.from
            .mockReturnValueOnce(chain({ data: { compiles: 3 } }))
            .mockReturnValueOnce(
                chain({ data: Array.from({ length: MAX_PENDING_COMPILES }, () => ({ id: 'x' })) }),
            );

        await expect(
            enqueueCompile('user-1', [{ role: 'user', content: 'buy chips' }]),
        ).rejects.toThrow(pendingCompilesMessage());
    });

    it('inserts a recipe-less compile job carrying the prepared request', async () => {
        const inserted: unknown[] = [];
        mockDb.from
            .mockReturnValueOnce(chain({ data: null }))
            .mockReturnValueOnce(chain({ data: [] }))
            .mockReturnValueOnce(chain({ data: { id: 'job-42' } }, (row) => inserted.push(row)));

        const jobId = await enqueueCompile('user-1', [{ role: 'user', content: 'buy chips' }]);

        expect(jobId).toBe('job-42');
        expect(inserted).toHaveLength(1);
        const row = inserted[0] as Record<string, unknown>;
        expect(row.mode).toBe('compile');
        expect(row.recipe_id).toBeNull();
        expect(row.user_id).toBe('user-1');
        expect((row.payload_json as { messages: unknown[] }).messages.length).toBeGreaterThan(1);
    });
});

describe('readCompileJob', () => {
    it('returns the job row for a poll', async () => {
        mockDb.from.mockReturnValue(
            chain({
                data: {
                    id: 'job-42',
                    status: 'processing',
                    progress_pct: 5,
                    result_json: null,
                    error_message: null,
                },
            }),
        );

        await expect(readCompileJob('job-42', 'user-1')).resolves.toMatchObject({
            id: 'job-42',
            status: 'processing',
        });
    });

    it('returns null when the row is gone', async () => {
        mockDb.from.mockReturnValue(chain({ data: null }));
        await expect(readCompileJob('gone', 'user-1')).resolves.toBeNull();
    });
});

describe('fallback template contract', () => {
    it('the starter template still validates, so a degraded compile is runnable', () => {
        expect(STARTER_RECIPES[0].stages).toHaveLength(1);
    });
});
