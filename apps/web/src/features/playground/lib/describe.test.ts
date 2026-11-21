import { describe, expect, it } from 'vitest';
import type { PushStrategy } from '~/features/recipes/types';
import { interpretReply } from './describe';

const strategy = {
    version: '2.0-push',
    name: 'Chip momentum',
    cadence: '3h',
    stages: [{ id: 's1', blocks: [{ id: 'b1', type: 'output_format' }], selected_tools: [] }],
} as PushStrategy;

describe('interpretReply', () => {
    it('passes a compiled strategy through with its summary', () => {
        const read = interpretReply({ status: 'ok', strategy, summary: 'Buy chips on capex.' });
        expect(read.compiled?.summary).toBe('Buy chips on capex.');
        expect(read.note).toBe('Buy chips on capex.');
        expect(read.failed).toBeUndefined();
    });

    it('says a degraded answer is a starter, not the visitor idea', () => {
        const read = interpretReply({
            status: 'ok',
            strategy,
            summary: 'Could not parse',
            fallback: true,
        });
        expect(read.note).toMatch(/starter was loaded/);
        expect(read.compiled?.fallback).toBe(true);
    });

    it('returns a question without touching the draft', () => {
        const read = interpretReply({
            status: 'question',
            question: 'Long or short?',
            options: [],
        });
        expect(read.note).toBe('Long or short?');
        expect(read.compiled).toBeUndefined();
    });

    it('reports the closest buildable version for a declined idea', () => {
        const read = interpretReply({
            status: 'declined',
            reason: 'No shorts.',
            closest: 'Long-only version.',
        });
        expect(read.note).toContain('Long-only version.');
        expect(read.failed).toBe('No shorts.');
    });
});
