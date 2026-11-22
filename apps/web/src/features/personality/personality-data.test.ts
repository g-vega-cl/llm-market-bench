import { describe, expect, it } from 'vitest';
import { STARTER_RECIPES } from '../recipes/starter-templates';
import {
    ARCHETYPE_IDS,
    ARCHETYPES,
    type ArchetypeId,
    AXIS_DEFINITIONS,
    buildSharedArchetypeResult,
    codeFromAnswers,
    codeFromProfile,
    formatRecipeExecutionSpec,
    getRecipeForArchetype,
    isValidArchetypeId,
    isValidTypeCode,
    lettersForAnswers,
    neighbourForProfile,
    PERSONALITY_AXES,
    PERSONALITY_QUESTIONS,
    type PersonalityAxis,
    QUIZ_ACTS,
    scorePersonalityQuiz,
    summarizeRecipeCoreGate,
    TYPE_CODES,
    TYPE_GRID,
    TYPE_LETTERS,
} from './personality-data';

/** Deterministic xorshift32 so the distribution gate is stable in CI. */
function makeRng(seed: number): () => number {
    let state = seed >>> 0;
    return () => {
        state ^= state << 13;
        state >>>= 0;
        state ^= state >>> 17;
        state ^= state << 5;
        state >>>= 0;
        return state;
    };
}

const MAX_TARGET_DELTA = Math.max(
    ...PERSONALITY_QUESTIONS.flatMap((q) =>
        q.options.map((opt) => Math.abs(opt.deltas[q.act] ?? 0)),
    ),
);

function buildAnswersTowardProfile(
    target: (typeof ARCHETYPES)[ArchetypeId]['idealProfile'],
): Record<string, string> {
    const desired = PERSONALITY_AXES.reduce(
        (acc, axis) => {
            acc[axis] = ((target[axis] - 50) / 50) * MAX_TARGET_DELTA;
            return acc;
        },
        {} as Record<(typeof PERSONALITY_AXES)[number], number>,
    );
    const answers: Record<string, string> = {};

    for (const q of PERSONALITY_QUESTIONS) {
        let bestOpt = q.options[0];
        let bestDist = Infinity;
        for (const opt of q.options) {
            const dist =
                (desired.horizon - (opt.deltas.horizon ?? 0)) ** 2 +
                (desired.signal - (opt.deltas.signal ?? 0)) ** 2 +
                (desired.contrarian - (opt.deltas.contrarian ?? 0)) ** 2 +
                (desired.cadence - (opt.deltas.cadence ?? 0)) ** 2;
            if (dist < bestDist) {
                bestDist = dist;
                bestOpt = opt;
            }
        }
        answers[q.id] = bestOpt.id;
    }
    return answers;
}

function actMassFor(answers: Record<string, string>, axis: PersonalityAxis): number {
    return PERSONALITY_QUESTIONS.filter((q) => q.act === axis).reduce((sum, q) => {
        const chosen = q.options.find((o) => o.id === answers[q.id]);
        return sum + (chosen?.deltas[axis] ?? 0);
    }, 0);
}

/** Every emitted letter must match the sign of its own act's delta mass. */
function expectLettersMatchProbes(answers: Record<string, string>): void {
    for (const letter of scorePersonalityQuiz(answers).letters) {
        const mass = actMassFor(answers, letter.axis);
        if (mass === 0) continue;
        const expected = mass > 0 ? TYPE_LETTERS[letter.axis].high : TYPE_LETTERS[letter.axis].low;
        expect(letter.letter).toBe(expected);
    }
}

describe('personality-data (16-question 4-axis diagnostic, 16-cell type grid)', () => {
    it('defines 16 questions across 4 acts of 4 with 1:1 archetype-recipe integrity', () => {
        expect(PERSONALITY_QUESTIONS).toHaveLength(16);
        expect(QUIZ_ACTS).toHaveLength(4);

        for (const act of QUIZ_ACTS) {
            const inAct = PERSONALITY_QUESTIONS.filter((q) => q.act === act.axis);
            expect(inAct).toHaveLength(4);
        }

        const ids = new Set(PERSONALITY_QUESTIONS.map((q) => q.id));
        const optionIds = new Set<string>();
        expect(ids.size).toBe(16);
        for (const q of PERSONALITY_QUESTIONS) {
            expect(q.options).toHaveLength(4);
            for (const opt of q.options) {
                expect(optionIds.has(opt.id)).toBe(false);
                optionIds.add(opt.id);
            }
        }

        const recipeNames = new Set(STARTER_RECIPES.map((r) => r.name));
        const mappedRecipes = new Set(ARCHETYPE_IDS.map((id) => ARCHETYPES[id].recipeName));

        expect(AXIS_DEFINITIONS).toHaveLength(4);
        expect(mappedRecipes.size).toBe(16);
        expect(ARCHETYPE_IDS).toHaveLength(16);
        for (const name of mappedRecipes) {
            expect(recipeNames.has(name)).toBe(true);
        }
        expect(isValidArchetypeId('catalyst-quant')).toBe(true);
        expect(isValidArchetypeId('invalid')).toBe(false);
    });

    it('covers all 16 type cells with fixed-order letters and one archetype per claimed cell', () => {
        expect(TYPE_CODES).toHaveLength(16);
        expect(new Set(TYPE_CODES).size).toBe(16);
        expect(TYPE_GRID).toHaveLength(16);

        for (const code of TYPE_CODES) {
            expect(code).toHaveLength(4);
            expect(isValidTypeCode(code)).toBe(true);
            // Slot order: horizon, signal, stance, tempo.
            expect(
                code[0] === TYPE_LETTERS.horizon.low || code[0] === TYPE_LETTERS.horizon.high,
            ).toBe(true);
            expect(
                code[1] === TYPE_LETTERS.signal.low || code[1] === TYPE_LETTERS.signal.high,
            ).toBe(true);
            expect(
                code[2] === TYPE_LETTERS.contrarian.low || code[2] === TYPE_LETTERS.contrarian.high,
            ).toBe(true);
            expect(
                code[3] === TYPE_LETTERS.cadence.low || code[3] === TYPE_LETTERS.cadence.high,
            ).toBe(true);
        }

        expect(isValidTypeCode('lvfp')).toBe(false);
        expect(isValidTypeCode('XXXX')).toBe(false);
        expect(isValidTypeCode(null)).toBe(false);

        const claimed = ARCHETYPE_IDS.map((id) => ARCHETYPES[id].code);
        expect(new Set(claimed).size).toBe(claimed.length);
        for (const id of ARCHETYPE_IDS) {
            const cell = TYPE_GRID.find((c) => c.code === ARCHETYPES[id].code);
            expect(cell?.archetypeId).toBe(id);
        }
        // Every cell centroid must reproduce its own code.
        for (const cell of TYPE_GRID) {
            expect(codeFromProfile(cell.centroid)).toBe(cell.code);
        }
    });

    it('keeps cross-loadings small and symmetric while loading each question’s act axis', () => {
        for (const q of PERSONALITY_QUESTIONS) {
            for (const axis of PERSONALITY_AXES) {
                const values = q.options.map((o) => o.deltas[axis] ?? 0);
                // Symmetric about zero keeps the normalized midpoint at a true 50.
                expect(values[0] + values[3]).toBe(0);
                expect(values[1] + values[2]).toBe(0);
                for (const v of values) {
                    if (axis === q.act) {
                        // Target axis: strong and non-neutral on every option.
                        expect(Math.abs(v)).toBeGreaterThanOrEqual(5);
                    } else {
                        // Cross-loadings stay small: they shape the readout only,
                        // never the letter (see the probe-dominance test below).
                        expect(Math.abs(v)).toBeLessThanOrEqual(4);
                    }
                }
            }
        }
    });

    it('never lets cross-loadings outvote the four probes that define a letter', () => {
        // Answer every horizon probe impatiently while maximising horizon
        // cross-loadings on the other twelve questions: the letter must still be Q.
        const answers: Record<string, string> = {};
        for (const q of PERSONALITY_QUESTIONS) {
            const sorted = [...q.options].sort(
                (a, b) => (a.deltas[q.act] ?? 0) - (b.deltas[q.act] ?? 0),
            );
            if (q.act === 'horizon') answers[q.id] = sorted[0].id;
            else
                answers[q.id] = [...q.options].sort(
                    (a, b) => (b.deltas.horizon ?? 0) - (a.deltas.horizon ?? 0),
                )[0].id;
        }
        const result = scorePersonalityQuiz(answers);
        expect(result.letters[0].letter).toBe('Q');
        expect(result.letters[0].strength).toBe('clear');
    });

    it('always derives each letter from its own act probes over random answer sets', () => {
        const rng = makeRng(0x5eed);
        for (let i = 0; i < 2_000; i++) {
            const answers: Record<string, string> = {};
            for (const q of PERSONALITY_QUESTIONS) {
                answers[q.id] = q.options[(rng() >>> 16) % 4].id;
            }
            const result = scorePersonalityQuiz(answers);
            expect(result.letters).toHaveLength(4);
            expectLettersMatchProbes(answers);
        }
    });

    it('keeps every one of the 16 type cells reachable and populated (distribution gate)', () => {
        const SAMPLES = 200_000;
        const rng = makeRng(0xc0ffee);
        const counts = new Map<string, number>();

        for (let i = 0; i < SAMPLES; i++) {
            const answers: Record<string, string> = {};
            for (const q of PERSONALITY_QUESTIONS) {
                answers[q.id] = q.options[(rng() >>> 16) % 4].id;
            }
            const code = codeFromAnswers(answers);
            counts.set(code, (counts.get(code) ?? 0) + 1);
        }

        expect(counts.size).toBe(16);
        for (const code of TYPE_CODES) {
            const seen = counts.get(code) ?? 0;
            expect(seen, `cell ${code} observed ${seen} times`).toBeGreaterThanOrEqual(500);
            expect(seen / SAMPLES, `cell ${code} share`).toBeGreaterThanOrEqual(0.02);
        }
    });

    it('keeps all 120 archetype recipe pairs structurally distinct', () => {
        interface RecipeSignature {
            news: number | 'none';
            mem: number | 'none';
            rules: string;
            tools: string;
        }

        const signature = (archetypeId: ArchetypeId): RecipeSignature => {
            const stage = getRecipeForArchetype(archetypeId).stages[0];
            const news = stage.blocks.find((block) => block.type === 'news');
            const memories = stage.blocks.find((block) => block.type === 'memories');
            const rules = stage.blocks
                .flatMap((block) => (block.type === 'technicals' ? block.rules : []))
                .map((rule) => `${rule.metric}${rule.operator}${rule.target}`)
                .sort()
                .join('|');
            return {
                news: news?.recency_hours ?? 'none',
                mem: memories?.recency_hours ?? 'none',
                rules,
                tools: [...stage.selected_tools].sort().join('|'),
            };
        };

        const dimensions = ['news', 'mem', 'rules', 'tools'] as const;
        const collisions: string[] = [];

        for (let i = 0; i < ARCHETYPE_IDS.length; i++) {
            for (let j = i + 1; j < ARCHETYPE_IDS.length; j++) {
                const left = signature(ARCHETYPE_IDS[i]);
                const right = signature(ARCHETYPE_IDS[j]);
                const differing = dimensions.filter((key) => left[key] !== right[key]);
                if (differing.length < 2) {
                    collisions.push(
                        `${ARCHETYPE_IDS[i]}/${ARCHETYPE_IDS[j]}: ${differing.join(',')}`,
                    );
                }
            }
        }

        expect(collisions).toEqual([]);
    });

    it('gives every archetype a distinct title, prompt and recipe prompt', () => {
        expect(new Set(ARCHETYPE_IDS.map((id) => ARCHETYPES[id].title)).size).toBe(16);
        expect(new Set(ARCHETYPE_IDS.map((id) => ARCHETYPES[id].recipeName)).size).toBe(16);
        expect(new Set(ARCHETYPE_IDS.map((id) => ARCHETYPES[id].builderIdeaPrompt)).size).toBe(16);

        const prompts = ARCHETYPE_IDS.map((id) => {
            const blocks = getRecipeForArchetype(id).stages[0].blocks;
            return blocks.find((block) => block.type === 'prompt')?.text ?? '';
        });
        expect(prompts.every((text) => text.length >= 100)).toBe(true);
        expect(new Set(prompts).size).toBe(16);
    });

    it('reaches every single one of the 5 archetypes with top-2 distinct matches and bounded 0..100 axes', () => {
        const reached = new Set<ArchetypeId>();

        for (const targetId of ARCHETYPE_IDS) {
            const answers = buildAnswersTowardProfile(ARCHETYPES[targetId].idealProfile);
            const result = scorePersonalityQuiz(answers);
            expect(result.answeredCount).toBe(16);
            expect(result.primary.archetype.id).toBe(targetId);
            // The emitted code must be the archetype's own cell, not a near neighbour.
            expect(result.code).toBe(ARCHETYPES[targetId].code);
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

    it('emits the fixed-order code with count-based strength labels', () => {
        // Highest-delta option of each question is the high pole (option order rotates).
        const highAnswers: Record<string, string> = {};
        const lowAnswers: Record<string, string> = {};
        for (const q of PERSONALITY_QUESTIONS) {
            const byActDelta = [...q.options].sort(
                (a, b) => (b.deltas[q.act] ?? 0) - (a.deltas[q.act] ?? 0),
            );
            highAnswers[q.id] = byActDelta[0].id;
            lowAnswers[q.id] = byActDelta[3].id;
        }

        const high = scorePersonalityQuiz(highAnswers);
        expect(high.code).toBe('LNFR');
        expect(high.letters.map((l) => l.strength)).toEqual(['clear', 'clear', 'clear', 'clear']);
        expect(high.letters.map((l) => l.axis)).toEqual([
            'horizon',
            'signal',
            'contrarian',
            'cadence',
        ]);

        const low = scorePersonalityQuiz(lowAnswers);
        expect(low.code).toBe('QVMP');
        const weakest = low.neighbour;
        expect(weakest).not.toBeNull();
        const slot = ['horizon', 'signal', 'contrarian', 'cadence'].indexOf(
            weakest?.axis ?? 'horizon',
        );
        const flipped = low.code.split('');
        flipped[slot] = weakest?.letter ?? '';
        expect(weakest?.code).toBe(flipped.join(''));
        expect(flipped.filter((letter, i) => letter !== low.code[i])).toHaveLength(1);
    });

    it('marks near-boundary letters as toss-ups and flips the weakest letter for the neighbour', () => {
        const letters = lettersForAnswers(
            {},
            { horizon: 50, signal: 52, contrarian: 48, cadence: 70 },
        );
        expect(letters.map((l) => l.tossUp)).toEqual([true, true, true, false]);
        // No probes answered yet, so strength is honest and weak.
        expect(letters.every((l) => l.strength === 'slight')).toBe(true);

        // Weakest axis wins on the smallest margin, ties resolved by slot order.
        const nearest = neighbourForProfile({
            horizon: 61,
            signal: 50,
            contrarian: 50,
            cadence: 82,
        });
        expect(nearest?.axis).toBe('signal');
        expect(nearest?.letter).toBe('N');
        expect(nearest?.code).toBe('LNMR');

        const empty = scorePersonalityQuiz({});
        expect(empty.neighbour).toBeNull();
        expect(empty.answeredCount).toBe(0);
        expect(empty.code).toBe('QVMP');
    });

    it('derives execution spec and <= 14-char core gate tokens directly from starter recipes', () => {
        for (const id of ARCHETYPE_IDS) {
            const recipe = getRecipeForArchetype(id);
            const execSpec = formatRecipeExecutionSpec(recipe);
            const coreGate = summarizeRecipeCoreGate(recipe);

            expect(coreGate.length).toBeGreaterThan(0);
            expect(coreGate.length).toBeLessThanOrEqual(14);

            const blocks = recipe.stages[0]?.blocks ?? [];
            const news = blocks.find((b) => b.type === 'news');
            const memories = blocks.find((b) => b.type === 'memories');
            const technicals = blocks.find((b) => b.type === 'technicals');

            if (news) {
                expect(execSpec).toContain(`News ${news.recency_hours}h`);
            } else {
                expect(execSpec).toContain('News Off');
            }
            if (memories) {
                expect(execSpec).toContain(`Memory ${memories.recency_hours}h`);
            }
            for (const rule of technicals?.rules ?? []) {
                expect(execSpec).toContain(`${rule.operator} ${rule.target}`);
            }
        }

        // Core gate preserves arbitrary operators and stays <= 14 chars even on 3-digit windows
        const synthetic = getRecipeForArchetype('news-surfer');
        expect(
            summarizeRecipeCoreGate({
                ...synthetic,
                stages: [
                    {
                        ...synthetic.stages[0],
                        blocks: [
                            { id: 'n', type: 'news', contains: ['ai'], recency_hours: 168 },
                            {
                                id: 't',
                                type: 'technicals',
                                rules: [
                                    {
                                        id: 'r',
                                        metric: 'price_52w_pct',
                                        operator: '>',
                                        target: '85',
                                    },
                                ],
                            },
                        ],
                    },
                ],
            }).length,
        ).toBeLessThanOrEqual(14);
        const valueRecipe = getRecipeForArchetype('value-compounder');
        const valueGateGt = summarizeRecipeCoreGate({
            ...valueRecipe,
            stages: [
                {
                    ...valueRecipe.stages[0],
                    blocks: [
                        {
                            id: 't',
                            type: 'technicals',
                            rules: [
                                { id: 'r', metric: 'price_52w_pct', operator: '>', target: '85' },
                            ],
                        },
                    ],
                },
            ],
        });
        expect(valueGateGt).toBe('>85% 52w');
    });

    it('builds valid shareable archetype results directly for every archetype id', () => {
        for (const id of ARCHETYPE_IDS) {
            const shared = buildSharedArchetypeResult(id);
            expect(shared.primary.archetype.id).toBe(id);
            expect(shared.primary.recipe.name).toBe(ARCHETYPES[id].recipeName);
            expect(shared.primary.fitPercent).toBe(98);
            expect(shared.runnerUp.archetype.id).not.toBe(id);
            expect(shared.code).toBe(ARCHETYPES[id].code);
            // The neighbour is always exactly one letter away from the shared code.
            expect(shared.neighbour).not.toBeNull();
            const code = shared.code.split('');
            const neighbour = (shared.neighbour?.code ?? '').split('');
            expect(neighbour).toHaveLength(4);
            expect(neighbour.filter((letter, i) => letter !== code[i])).toHaveLength(1);
        }
    });
});
