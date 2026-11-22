import { describe, expect, it } from 'vitest';
import { STARTER_RECIPES } from '../recipes/starter-templates';
import {
    ARCHETYPE_IDS,
    ARCHETYPES,
    type ArchetypeId,
    AXIS_DEFINITIONS,
    buildSharedArchetypeResult,
    isValidArchetypeId,
    PERSONALITY_QUESTIONS,
    scorePersonalityQuiz,
} from './personality-data';

describe('personality-data (10-question 4-axis diagnostic & starter bot matcher)', () => {
    it('defines 10 questions with 4 distinct options and 1:1 archetype-recipe integrity', () => {
        expect(PERSONALITY_QUESTIONS).toHaveLength(10);
        for (const q of PERSONALITY_QUESTIONS) {
            expect(q.options).toHaveLength(4);
        }

        const recipeNames = new Set(STARTER_RECIPES.map((r) => r.name));
        const mappedRecipes = new Set(ARCHETYPE_IDS.map((id) => ARCHETYPES[id].recipeName));

        expect(AXIS_DEFINITIONS).toHaveLength(4);
        expect(mappedRecipes.size).toBe(5);
        for (const name of mappedRecipes) {
            expect(recipeNames.has(name)).toBe(true);
        }
        expect(isValidArchetypeId('catalyst-quant')).toBe(true);
        expect(isValidArchetypeId('invalid')).toBe(false);
    });

    it('reaches every single one of the 5 archetypes with top-2 distinct matches and bounded 0..100 axes', () => {
        const reached = new Set<ArchetypeId>();

        for (const targetId of ARCHETYPE_IDS) {
            const target = ARCHETYPES[targetId].idealProfile;
            const answers: Record<string, string> = {};

            for (const q of PERSONALITY_QUESTIONS) {
                const desiredHorizon = ((target.horizon - 50) / 50) * 14;
                const desiredSignal = ((target.signal - 50) / 50) * 14;
                const desiredContrarian = ((target.contrarian - 50) / 50) * 14;
                const desiredCadence = ((target.cadence - 50) / 50) * 14;

                let bestOpt = q.options[0];
                let bestDist = Infinity;
                for (const opt of q.options) {
                    const dist =
                        (desiredHorizon - (opt.deltas.horizon ?? 0)) ** 2 +
                        (desiredSignal - (opt.deltas.signal ?? 0)) ** 2 +
                        (desiredContrarian - (opt.deltas.contrarian ?? 0)) ** 2 +
                        (desiredCadence - (opt.deltas.cadence ?? 0)) ** 2;
                    if (dist < bestDist) {
                        bestDist = dist;
                        bestOpt = opt;
                    }
                }
                answers[q.id] = bestOpt.id;
            }

            const result = scorePersonalityQuiz(answers);
            expect(result.answeredCount).toBe(10);
            expect(result.primary.archetype.id).toBe(targetId);
            expect(result.primary.archetype.id).not.toBe(result.runnerUp.archetype.id);
            expect(result.primary.fitPercent).toBeGreaterThanOrEqual(result.runnerUp.fitPercent);
            for (const axis of AXIS_DEFINITIONS) {
                expect(result.profile[axis.id]).toBeGreaterThanOrEqual(0);
                expect(result.profile[axis.id]).toBeLessThanOrEqual(100);
            }
            reached.add(result.primary.archetype.id);
        }

        expect(reached).toEqual(new Set(ARCHETYPE_IDS));
    });

    it('builds valid shareable archetype results directly for every archetype id', () => {
        for (const id of ARCHETYPE_IDS) {
            const shared = buildSharedArchetypeResult(id);
            expect(shared.primary.archetype.id).toBe(id);
            expect(shared.primary.recipe.name).toBe(ARCHETYPES[id].recipeName);
            expect(shared.primary.fitPercent).toBe(98);
            expect(shared.runnerUp.archetype.id).not.toBe(id);
        }
    });
});
