import { beforeEach, describe, expect, it } from 'vitest';
import type { PushStrategy } from '../types';
import {
    clearLocalDraft,
    clearPendingIdea,
    DRAFT_STORAGE_KEY,
    loadLocalDraft,
    loadPendingIdea,
    saveLocalDraft,
    savePendingIdea,
} from './local-draft';

const strategy = {
    version: '2.0-push',
    name: 'Chip Momentum',
    cadence: '3h',
    stages: [{ id: 's1', blocks: [{ id: 'b1', type: 'output_format' }], selected_tools: [] }],
} as PushStrategy;

describe('local recipe draft', () => {
    beforeEach(() => {
        window.localStorage.clear();
    });

    it('round-trips a draft with its source and timestamp', () => {
        saveLocalDraft(strategy, 'builder');
        const draft = loadLocalDraft();
        expect(draft?.strategy.name).toBe('Chip Momentum');
        expect(draft?.source).toBe('builder');
        expect(typeof draft?.savedAt).toBe('string');
    });

    it('returns null for malformed storage instead of throwing', () => {
        window.localStorage.setItem(DRAFT_STORAGE_KEY, '{not json');
        expect(loadLocalDraft()).toBeNull();
    });

    it('ignores a draft whose graph is not single-stage', () => {
        window.localStorage.setItem(
            DRAFT_STORAGE_KEY,
            JSON.stringify({
                strategy: { ...strategy, stages: [] },
                savedAt: 'x',
                source: 'studio',
            }),
        );
        expect(loadLocalDraft()).toBeNull();
    });

    it('clears the draft', () => {
        saveLocalDraft(strategy);
        clearLocalDraft();
        expect(loadLocalDraft()).toBeNull();
    });
});

describe('pending builder idea', () => {
    beforeEach(() => {
        window.localStorage.clear();
    });

    it('keeps the anonymous message across the login redirect', () => {
        savePendingIdea('buy chips on capex news');
        expect(loadPendingIdea()).toBe('buy chips on capex news');
    });

    it('ignores a blank idea', () => {
        savePendingIdea('   ');
        expect(loadPendingIdea()).toBeNull();
    });

    it('clears the pending idea once the recipe is compiled', () => {
        savePendingIdea('buy chips');
        clearPendingIdea();
        expect(loadPendingIdea()).toBeNull();
    });
});
