import { STARTER_RECIPES } from '../recipes/starter-templates';
import type { PushStrategy } from '../recipes/types';
import {
    ARCHETYPE_IDS,
    ARCHETYPES,
    type ArchetypeId,
    assertValidArchetypeGrid,
    type InvestingArchetype,
} from './personality-archetypes';
import { type AxisProfile, PERSONALITY_AXES, type PersonalityAxis } from './personality-axes';
import {
    type LetterStrength,
    letterForValue,
    type NeighbourResult,
    neighbourForProfile,
    TYPE_LETTERS,
    TYPE_SLOT_ORDER,
    type TypeCode,
    type TypeLetter,
} from './personality-type-grid';
import { PERSONALITY_QUESTIONS, type QuizQuestion } from './questions';

export {
    ARCHETYPE_IDS,
    ARCHETYPES,
    type ArchetypeId,
    type InvestingArchetype,
    isValidArchetypeId,
    TYPE_GRID,
    type TypeCell,
} from './personality-archetypes';
// Public surface preserved: callers keep importing everything from `personality-data`.
export * from './personality-axes';
export { formatRecipeExecutionSpec, summarizeRecipeCoreGate } from './personality-recipe-spec';
export {
    centroidForCode,
    codeFromProfile,
    isValidTypeCode,
    type LetterStrength,
    letterForValue,
    lettersOfCode,
    type NeighbourResult,
    neighbourForProfile,
    TYPE_CODES,
    TYPE_LETTERS,
    TYPE_SLOT_ORDER,
    type TypeCode,
    type TypeLetter,
} from './personality-type-grid';
export {
    PERSONALITY_QUESTIONS,
    QUIZ_ACTS,
    type QuizActDefinition,
    type QuizOption,
    type QuizQuestion,
} from './questions';

assertValidArchetypeGrid();

export interface ArchetypeMatch {
    archetype: InvestingArchetype;
    recipe: PushStrategy;
    fitPercent: number;
    distance: number;
}

export interface AxisLetterResult {
    axis: PersonalityAxis;
    letter: TypeLetter;
    value: number;
    strength: LetterStrength;
    /** True when the value sits within +-2 of the pole boundary. */
    tossUp: boolean;
}

export interface QuizScoreResult {
    profile: AxisProfile;
    primary: ArchetypeMatch;
    runnerUp: ArchetypeMatch;
    rankings: ArchetypeMatch[];
    answeredCount: number;
    /** Fixed-order four-letter code, e.g. `LVFP`. */
    code: TypeCode;
    letters: AxisLetterResult[];
    /** One-letter-away type on the weakest axis; null before the first answer. */
    neighbour: NeighbourResult | null;
}

const recipeByName = new Map<string, PushStrategy>(
    STARTER_RECIPES.map((recipe) => [recipe.name, recipe]),
);

/** Recipe name -> type code, for surfaces that list recipes rather than types. */
export const CODE_BY_RECIPE_NAME: ReadonlyMap<string, TypeCode> = new Map(
    ARCHETYPE_IDS.map((id) => [ARCHETYPES[id].recipeName, ARCHETYPES[id].code]),
);

// Validate 1:1 archetype -> starter-recipe integrity eagerly at module load.
for (const id of ARCHETYPE_IDS) {
    const expectedName = ARCHETYPES[id].recipeName;
    if (!recipeByName.has(expectedName)) {
        throw new Error(`Archetype "${id}" references missing starter recipe "${expectedName}"`);
    }
}

export function getRecipeForArchetype(archetypeId: ArchetypeId): PushStrategy {
    const recipeName = ARCHETYPES[archetypeId].recipeName;
    const found = recipeByName.get(recipeName);
    if (!found) {
        throw new Error(`Starter recipe "${recipeName}" missing for archetype "${archetypeId}"`);
    }
    return found;
}

function questionAxisRange(question: QuizQuestion, axis: PersonalityAxis) {
    let qMin = Number.POSITIVE_INFINITY;
    let qMax = Number.NEGATIVE_INFINITY;
    for (const opt of question.options) {
        const d = opt.deltas[axis] ?? 0;
        if (d < qMin) qMin = d;
        if (d > qMax) qMax = d;
    }
    return { qMin, qMax };
}

function accumulateAxisTotals(answers: Partial<Record<string, string>>) {
    const rawSum: AxisProfile = { horizon: 0, signal: 0, contrarian: 0, cadence: 0 };
    const minBound: AxisProfile = { horizon: 0, signal: 0, contrarian: 0, cadence: 0 };
    const maxBound: AxisProfile = { horizon: 0, signal: 0, contrarian: 0, cadence: 0 };
    let answeredCount = 0;

    for (const question of PERSONALITY_QUESTIONS) {
        const chosenId = answers[question.id];
        const chosen = chosenId ? question.options.find((opt) => opt.id === chosenId) : undefined;
        if (!chosen) continue;
        answeredCount++;

        for (const axis of PERSONALITY_AXES) {
            rawSum[axis] += chosen.deltas[axis] ?? 0;
            const { qMin, qMax } = questionAxisRange(question, axis);
            minBound[axis] += qMin;
            maxBound[axis] += qMax;
        }
    }

    return { answeredCount, rawSum, minBound, maxBound };
}

function normalizeAxisProfile(
    answeredCount: number,
    rawSum: AxisProfile,
    minBound: AxisProfile,
    maxBound: AxisProfile,
): AxisProfile {
    const profile: AxisProfile = { horizon: 50, signal: 50, contrarian: 50, cadence: 50 };
    if (answeredCount === 0) return profile;

    for (const axis of PERSONALITY_AXES) {
        const span = maxBound[axis] - minBound[axis];
        if (span > 0) {
            const norm = ((rawSum[axis] - minBound[axis]) / span) * 100;
            profile[axis] = Math.round(Math.max(0, Math.min(100, norm)));
        }
    }
    return profile;
}

/** Normalizes an answer set into the 4-axis profile (the first scoring stage). */
export function profileFromAnswers(answers: Partial<Record<string, string>>): AxisProfile {
    const { answeredCount, rawSum, minBound, maxBound } = accumulateAxisTotals(answers);
    return normalizeAxisProfile(answeredCount, rawSum, minBound, maxBound);
}

/**
 * Counts only the questions that belong to `axis` (its own act probes), so a
 * strength of "clear" always means 4 of 4 dedicated probes agreed.
 */
function actVotes(
    answers: Partial<Record<string, string>>,
    axis: PersonalityAxis,
): { high: number; low: number } {
    const votes = { high: 0, low: 0 };
    for (const question of PERSONALITY_QUESTIONS) {
        if (question.act !== axis) continue;
        const chosenId = answers[question.id];
        const chosen = chosenId ? question.options.find((opt) => opt.id === chosenId) : undefined;
        if (!chosen) continue;
        const delta = chosen.deltas[axis] ?? 0;
        if (delta > 0) votes.high++;
        else if (delta < 0) votes.low++;
    }
    return votes;
}

/**
 * Delta mass the act's own probes awarded on `axis`. The letter comes from this,
 * not from the pooled profile: cross-loadings from the other twelve questions
 * must never outvote the four questions that were asked about this axis.
 */
function actDeltaMass(answers: Partial<Record<string, string>>, axis: PersonalityAxis): number {
    let sum = 0;
    for (const question of PERSONALITY_QUESTIONS) {
        if (question.act !== axis) continue;
        const chosenId = answers[question.id];
        const chosen = chosenId ? question.options.find((opt) => opt.id === chosenId) : undefined;
        if (chosen) sum += chosen.deltas[axis] ?? 0;
    }
    return sum;
}

function letterFromProbes(
    answers: Partial<Record<string, string>>,
    axis: PersonalityAxis,
    profileValue: number,
): TypeLetter {
    const mass = actDeltaMass(answers, axis);
    if (mass > 0) return TYPE_LETTERS[axis].high;
    if (mass < 0) return TYPE_LETTERS[axis].low;
    // Exact tie (or no probes answered): fall back to the pooled profile.
    return letterForValue(axis, profileValue);
}

function strengthFromVotes(
    votes: { high: number; low: number },
    letter: TypeLetter,
    axis: PersonalityAxis,
): LetterStrength {
    const agreesWithHigh = letter === TYPE_LETTERS[axis].high;
    const agreeing = agreesWithHigh ? votes.high : votes.low;
    const disagreeing = agreesWithHigh ? votes.low : votes.high;
    // A split verdict, or a magnitude that contradicts the count, is honest: slight.
    if (agreeing <= disagreeing) return 'slight';
    if (agreeing >= 4) return 'clear';
    if (agreeing === 3) return 'moderate';
    return 'slight';
}

export function lettersForAnswers(
    answers: Partial<Record<string, string>>,
    profile: AxisProfile,
): AxisLetterResult[] {
    return TYPE_SLOT_ORDER.map((axis) => {
        const letter = letterFromProbes(answers, axis, profile[axis]);
        return {
            axis,
            letter,
            value: profile[axis],
            strength: strengthFromVotes(actVotes(answers, axis), letter, axis),
            tossUp: Math.abs(profile[axis] - 50) <= 2,
        };
    });
}

/** The code the quiz actually emits, without ranking archetypes (used by gates). */
export function codeFromAnswers(answers: Partial<Record<string, string>>): TypeCode {
    const profile = profileFromAnswers(answers);
    return lettersForAnswers(answers, profile)
        .map((l) => l.letter)
        .join('') as TypeCode;
}

function hammingToCode(code: TypeCode, candidate: TypeCode): number {
    let diff = 0;
    for (let i = 0; i < code.length; i++) {
        if (code[i] !== candidate[i]) diff++;
    }
    return diff;
}

function rankArchetypesForProfile(
    profile: AxisProfile,
    code: TypeCode,
    preferredArchetype?: ArchetypeId,
): ArchetypeMatch[] {
    return ARCHETYPE_IDS.map((id) => {
        const archetype = ARCHETYPES[id];
        const sq =
            (profile.horizon - archetype.idealProfile.horizon) ** 2 +
            (profile.signal - archetype.idealProfile.signal) ** 2 +
            (profile.contrarian - archetype.idealProfile.contrarian) ** 2 +
            (profile.cadence - archetype.idealProfile.cadence) ** 2;
        const distance = Math.sqrt(sq / PERSONALITY_AXES.length);
        const fitPercent =
            preferredArchetype === id
                ? 98
                : Math.round(Math.max(18, Math.min(99, 100 - distance * 0.95)));
        return { archetype, recipe: getRecipeForArchetype(id), fitPercent, distance };
    }).sort((a, b) => {
        const diff = a.distance - b.distance;
        if (Math.abs(diff) > 1e-9) return diff;
        // Corner centroids tie often, so prefer the archetype sharing the most
        // letters with the visitor's code before falling back to declaration order.
        const codeDiff =
            hammingToCode(code, a.archetype.code) - hammingToCode(code, b.archetype.code);
        if (codeDiff !== 0) return codeDiff;
        return ARCHETYPE_IDS.indexOf(a.archetype.id) - ARCHETYPE_IDS.indexOf(b.archetype.id);
    });
}

export function scorePersonalityQuiz(answers: Partial<Record<string, string>>): QuizScoreResult {
    const { answeredCount, rawSum, minBound, maxBound } = accumulateAxisTotals(answers);
    const profile = normalizeAxisProfile(answeredCount, rawSum, minBound, maxBound);
    const letters = lettersForAnswers(answers, profile);
    const code = letters.map((l) => l.letter).join('') as TypeCode;
    const rankings = rankArchetypesForProfile(profile, code);

    return {
        profile,
        primary: rankings[0],
        runnerUp: rankings[1],
        rankings,
        answeredCount,
        code,
        letters,
        neighbour: answeredCount === 0 ? null : neighbourForProfile(profile),
    };
}

/**
 * Renders a type's canonical result for a share link. Nothing was measured here,
 * so `answeredCount` is 0 and the letters describe the cell, not the visitor.
 */
export function buildSharedArchetypeResult(archetypeId: ArchetypeId): QuizScoreResult {
    const profile = { ...ARCHETYPES[archetypeId].idealProfile };
    const letters: AxisLetterResult[] = TYPE_SLOT_ORDER.map((axis) => ({
        axis,
        letter: letterForValue(axis, profile[axis]),
        value: profile[axis],
        strength: 'clear',
        tossUp: false,
    }));
    const code = letters.map((l) => l.letter).join('') as TypeCode;
    const rankings = rankArchetypesForProfile(profile, code, archetypeId);
    return {
        profile,
        primary: rankings[0],
        runnerUp: rankings[1],
        rankings,
        answeredCount: 0,
        code,
        letters,
        neighbour: neighbourForProfile(profile),
    };
}
