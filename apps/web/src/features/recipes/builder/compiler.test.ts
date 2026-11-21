import { describe, expect, it } from 'vitest';
import {
    buildConversation,
    capabilityManifest,
    fallbackReply,
    normalizeBlockOrder,
    parseCompilerReply,
    validateStrategy,
} from './compiler';

const validStrategy = {
    version: '2.0-push',
    name: 'Chip Momentum',
    description: 'Buys chipmakers on positive capex news',
    cadence: '3h',
    stages: [
        {
            id: 's1',
            blocks: [
                { id: 'b1', type: 'prompt', text: 'Buy the strongest chipmaker on capex news.' },
                { id: 'b2', type: 'news', contains: ['capex'], recency_hours: 48 },
                { id: 'b3', type: 'output_format' },
            ],
            selected_tools: ['get_stock_quote'],
        },
    ],
};

describe('capability manifest', () => {
    it('never offers web_search as a callable tool', () => {
        expect(capabilityManifest()).not.toContain('- web_search');
        expect(capabilityManifest()).toContain('Never use web_search');
    });

    it('lists the five blocks and the hard constraints', () => {
        const manifest = capabilityManifest();
        for (const block of ['prompt', 'news', 'memories', 'technicals', 'output_format']) {
            expect(manifest).toContain(`"type":"${block}"`);
        }
        expect(manifest).toContain('Long only');
        expect(manifest).toContain('Exactly one stage');
    });
});

describe('validateStrategy', () => {
    it('accepts a well-formed single-stage recipe', () => {
        const strategy = validateStrategy(structuredClone(validStrategy));
        expect(strategy.stages).toHaveLength(1);
        expect(strategy.name).toBe('Chip Momentum');
    });

    it('rejects a two-stage graph', () => {
        const broken = structuredClone(validStrategy);
        broken.stages.push(structuredClone(validStrategy.stages[0]));
        expect(() => validateStrategy(broken)).toThrow();
    });

    it('rejects a graph without an output_format block', () => {
        const broken = structuredClone(validStrategy);
        broken.stages[0].blocks = broken.stages[0].blocks.filter(
            (block) => block.type !== 'output_format',
        );
        expect(() => validateStrategy(broken)).toThrow(/output_format/);
    });

    it('rejects tools the engine does not allow in recipes', () => {
        const broken = structuredClone(validStrategy);
        broken.stages[0].selected_tools = ['web_search'];
        expect(() => validateStrategy(broken)).toThrow(/web_search|not available/);
    });

    it('rejects an invented block type', () => {
        const broken = structuredClone(validStrategy) as unknown as {
            stages: Array<{ blocks: Array<Record<string, unknown>> }>;
        };
        broken.stages[0].blocks.push({ id: 'b9', type: 'options_chain' });
        expect(() => validateStrategy(broken)).toThrow(/malformed block|unknown/);
    });

    it('rejects a cadence the scheduler does not honour', () => {
        const broken = structuredClone(validStrategy) as unknown as { cadence: string };
        broken.cadence = '15m';
        expect(() => validateStrategy(broken)).toThrow(/cadence/);
    });
});

describe('parseCompilerReply', () => {
    it('parses a compiled recipe out of a fenced JSON reply', () => {
        const raw = `\`\`\`json\n${JSON.stringify({
            status: 'ok',
            summary: 'Chip momentum',
            strategy: validStrategy,
        })}\n\`\`\``;
        const reply = parseCompilerReply(raw);
        expect(reply.status).toBe('ok');
        if (reply.status === 'ok') expect(reply.strategy.name).toBe('Chip Momentum');
    });

    it('parses a clarifying question with options', () => {
        const reply = parseCompilerReply(
            JSON.stringify({
                status: 'question',
                question: 'Which tickers?',
                options: ['NVDA', 'AMD'],
            }),
        );
        expect(reply).toEqual({
            status: 'question',
            question: 'Which tickers?',
            options: ['NVDA', 'AMD'],
        });
    });

    it('parses a decline with the closest buildable idea', () => {
        const reply = parseCompilerReply(
            JSON.stringify({
                status: 'declined',
                reason: 'Shorting is not supported',
                closest: 'Long-only version that exits on weakness',
            }),
        );
        expect(reply.status).toBe('declined');
    });

    it('throws on prose instead of JSON so the caller can retry', () => {
        expect(() => parseCompilerReply('Sure! Here is a strategy:')).toThrow();
    });

    it('throws when an ok reply carries an invalid graph', () => {
        expect(() =>
            parseCompilerReply(
                JSON.stringify({ status: 'ok', summary: 'x', strategy: { version: '2.0-push' } }),
            ),
        ).toThrow();
    });
});

describe('fallbackReply', () => {
    it('degrades to a runnable starter template instead of failing', () => {
        const reply = fallbackReply('Could not build that idea');
        expect(reply.status).toBe('ok');
        if (reply.status === 'ok') {
            expect(reply.strategy.stages).toHaveLength(1);
            expect(reply.strategy.stages[0].blocks.some((b) => b.type === 'output_format')).toBe(
                true,
            );
        }
    });
});

describe('block contract', () => {
    const withBlocks = (blocks: unknown[]) => ({
        ...validStrategy,
        stages: [{ ...validStrategy.stages[0], blocks }],
    });

    it('normalises a terminal block stored before the content blocks', () => {
        const strategy = validateStrategy(
            withBlocks([
                { id: 'b1', type: 'output_format' },
                { id: 'b2', type: 'prompt', text: 'Buy chips.' },
            ]),
        );

        expect(strategy.stages[0].blocks.map((block) => block.type)).toEqual([
            'prompt',
            'output_format',
        ]);
    });

    it('rejects duplicate block ids', () => {
        expect(() =>
            validateStrategy(
                withBlocks([
                    { id: 'b1', type: 'prompt', text: 'x' },
                    { id: 'b1', type: 'output_format' },
                ]),
            ),
        ).toThrow(/unique/);
    });

    it('rejects a technicals rule carrying value instead of target', () => {
        expect(() =>
            validateStrategy(
                withBlocks([
                    {
                        id: 'b1',
                        type: 'technicals',
                        rules: [{ metric: 'RSI', operator: '<', value: 30 }],
                    },
                    { id: 'b2', type: 'output_format' },
                ]),
            ),
        ).toThrow(/malformed block/);
    });

    it('rejects a memories block whose contains is not a list of keywords', () => {
        expect(() =>
            validateStrategy(
                withBlocks([
                    { id: 'b1', type: 'memories', contains: 'capex', recency_hours: 168 },
                    { id: 'b2', type: 'output_format' },
                ]),
            ),
        ).toThrow(/malformed block/);
    });

    it('teaches the engine field name in the capability manifest', () => {
        const manifest = capabilityManifest();
        expect(manifest).toContain('"target"');
        expect(manifest).not.toContain('"value"');
    });

    it('leaves an already-correct order untouched', () => {
        const blocks = [
            { id: 'b1', type: 'prompt', text: 'x' },
            { id: 'b2', type: 'output_format' },
        ] as const;
        expect(normalizeBlockOrder([...blocks]).map((b) => b.id)).toEqual(['b1', 'b2']);
    });
});

describe('buildConversation', () => {
    it('puts the system prompt first and keeps the turns in order', () => {
        const conversation = buildConversation([
            { role: 'user', content: 'buy chips' },
            { role: 'assistant', content: 'Which tickers?' },
        ]);
        expect(conversation[0].role).toBe('system');
        expect(conversation[1]).toEqual({ role: 'user', content: 'buy chips' });
        expect(conversation[2]).toEqual({ role: 'assistant', content: 'Which tickers?' });
    });
});
