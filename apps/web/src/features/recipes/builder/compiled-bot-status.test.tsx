import { describe, expect, it } from 'vitest';
import type { RecipeSummaryItem } from '../types';
import { deriveWorkspaceStatus, resolveScheduledLive } from './compiled-bot-status';

function record(id: string, isLive: boolean): RecipeSummaryItem {
    return {
        id,
        name: `Bot ${id}`,
        cadence: '3h',
        is_live: isLive,
        trial_count: 1,
        updated_at: '2026-11-24T00:00:00Z',
    };
}

const ownedLive = { isLive: true, isOwner: true };

describe('resolveScheduledLive', () => {
    it('is unknown when neither the snapshot nor the capped list knows the bot', () => {
        expect(
            resolveScheduledLive({
                recipeId: 'r1',
                live: null,
                loadedRecipes: [],
                currentRecipes: [],
            }),
        ).toBeNull();
    });

    it('trusts an owned snapshot when the bot is outside the list window', () => {
        expect(
            resolveScheduledLive({
                recipeId: 'r1',
                live: ownedLive,
                loadedRecipes: [],
                currentRecipes: [],
            }),
        ).toBe(true);
    });

    it('ignores a snapshot for a bot the viewer does not own', () => {
        expect(
            resolveScheduledLive({
                recipeId: 'r1',
                live: { isLive: true, isOwner: false },
                loadedRecipes: [],
                currentRecipes: [],
            }),
        ).toBeNull();
    });

    it('prefers a row mutated on this page over the loader snapshot', () => {
        expect(
            resolveScheduledLive({
                recipeId: 'r1',
                live: { isLive: false, isOwner: true },
                loadedRecipes: [record('r1', false)],
                currentRecipes: [record('r1', true)],
            }),
        ).toBe(true);
    });

    it('falls back to the list when the snapshot could not be read', () => {
        expect(
            resolveScheduledLive({
                recipeId: 'r1',
                live: null,
                loadedRecipes: [record('r1', false)],
                currentRecipes: [record('r1', false)],
            }),
        ).toBe(false);
    });

    it('treats an unsaved draft as known-paused rather than unknown', () => {
        expect(
            resolveScheduledLive({
                recipeId: undefined,
                live: null,
                loadedRecipes: [],
                currentRecipes: [],
            }),
        ).toBe(false);
    });

    it('never advises going live on an unknown schedule', () => {
        const status = deriveWorkspaceStatus({
            hasEmptyPrompt: false,
            runInFlight: false,
            runView: null,
            isCurrentlyScheduledLive: null,
            fallback: false,
            hasLiveWarning: true,
            strategyId: 'r1',
            isDirty: false,
            statusDetail: 'Saved.',
        });
        expect(status.kind).toBe('saved');
        expect(status.showLiveWarning).toBe(false);
        expect(status.preferLive).toBe(false);
    });
});
