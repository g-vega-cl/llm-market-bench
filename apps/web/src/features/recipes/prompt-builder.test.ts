import { describe, expect, it } from 'vitest';
import {
    buildStagePromptPreview,
    hydrateMemoriesBlockText,
    hydrateNewsBlockText,
} from './prompt-builder';
import type { StrategyStage } from './types';

describe('prompt-builder', () => {
    it('builds unhydrated and hydrated stage prompt previews', () => {
        const stage: StrategyStage = {
            id: 'stage-1',
            selected_tools: [],
            blocks: [
                { id: 'b-prompt', type: 'prompt', text: 'Find semiconductor momentum.' },
                { id: 'b-news', type: 'news', contains: ['NVDA'], recency_hours: 24 },
                {
                    id: 'b-tech',
                    type: 'technicals',
                    rules: [{ id: 'r1', metric: 'RSI_14', operator: '<', target: '70' }],
                },
                { id: 'b-fmt', type: 'output_format' },
            ],
        };

        const raw = buildStagePromptPreview(stage);
        expect(raw).toContain('Find semiconductor momentum.');
        expect(raw).toContain('<Matching news headlines injected at run time>');
        expect(raw).toContain('- RSI_14 < 70');
        expect(raw).toContain('=== REQUIRED OUTPUT FORMAT ===');
        expect(raw).toContain('Long-Only');
        expect(raw).toContain('"BUY" or "EXIT"');

        const hydrated = buildStagePromptPreview(stage, {
            'b-news': '[News]:\n- NVDA breaks out on Blackwell guidance',
        });
        expect(hydrated).toContain('NVDA breaks out on Blackwell guidance');
    });

    it('filters news and memory rows by recency, keywords, category, and importance', () => {
        const now = Date.parse('2026-03-10T15:00:00Z');
        const newsOut = hydrateNewsBlockText(
            { contains: ['NVDA'], recency_hours: 12 },
            [
                {
                    title: 'NVDA beats estimates',
                    full_text: 'Strong NVDA datacenter demand.',
                    date_published: '2026-03-10T10:00:00Z',
                },
                {
                    title: 'Stale NVDA article',
                    full_text: 'Too old',
                    date_published: '2026-03-08T10:00:00Z',
                },
            ],
            now,
        );
        expect(newsOut).toContain('NVDA beats estimates');
        expect(newsOut).not.toContain('Stale NVDA article');

        const memOut = hydrateMemoriesBlockText(
            { contains: ['rates'], recency_hours: 24, category: 'MACRO', min_importance: 7 },
            [
                {
                    content: 'Fed signals steady rates',
                    created_at: '2026-03-10T12:00:00Z',
                    memory_type: 'MACRO',
                    importance_score: 8,
                },
                {
                    content: 'Minor rates chatter',
                    created_at: '2026-03-10T12:00:00Z',
                    memory_type: 'MACRO',
                    importance_score: 3,
                },
            ],
            now,
        );
        expect(memOut).toContain('Fed signals steady rates');
        expect(memOut).not.toContain('Minor rates chatter');
    });
});
