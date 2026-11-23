import { type AxisProfile, PERSONALITY_AXES, type PersonalityAxis } from './personality-axes';

/**
 * Fixed slot order for the four-letter code: horizon, signal, stance, tempo.
 * A fixed order keeps codes comparable between two people ("we're both LVFP")
 * and keeps share URLs stable. Conviction is communicated by a strength label,
 * never by reordering the letters.
 */
export const TYPE_SLOT_ORDER: PersonalityAxis[] = [...PERSONALITY_AXES];

export type TypeLetter = 'L' | 'Q' | 'V' | 'N' | 'M' | 'F' | 'P' | 'R';

export const TYPE_LETTERS: Record<
    PersonalityAxis,
    { readonly low: TypeLetter; readonly high: TypeLetter }
> = {
    horizon: { low: 'Q', high: 'L' },
    signal: { low: 'V', high: 'N' },
    contrarian: { low: 'M', high: 'F' },
    cadence: { low: 'P', high: 'R' },
};

/** Fixed-order four-letter personality code, e.g. `LVFP`. */
export type TypeCode = `${TypeLetter}${TypeLetter}${TypeLetter}${TypeLetter}`;

export type LetterStrength = 'clear' | 'moderate' | 'slight';

export const TYPE_CODES: readonly TypeCode[] = [
    'LVFP',
    'LVFR',
    'LVMP',
    'LVMR',
    'LNFP',
    'LNFR',
    'LNMP',
    'LNMR',
    'QVFP',
    'QVFR',
    'QVMP',
    'QVMR',
    'QNFP',
    'QNFR',
    'QNMP',
    'QNMR',
];

/** Canonical diagnostic counts (pinned to the bank and grid in personality-data.test.ts). */
export const PERSONALITY_QUESTION_COUNT = 16;
export const PERSONALITY_ARCHETYPE_COUNT = TYPE_CODES.length;

/** Grid corner centroid. The 16-cell grid deliberately has no middle. */
export const CENTROID_HIGH = 88;
export const CENTROID_LOW = 12;

export function isValidTypeCode(value: unknown): value is TypeCode {
    return typeof value === 'string' && (TYPE_CODES as readonly string[]).includes(value);
}

export function lettersOfCode(code: TypeCode): Record<PersonalityAxis, string> {
    return {
        horizon: code[0],
        signal: code[1],
        contrarian: code[2],
        cadence: code[3],
    };
}

export function letterForValue(axis: PersonalityAxis, value: number): TypeLetter {
    return value > 50 ? TYPE_LETTERS[axis].high : TYPE_LETTERS[axis].low;
}

export function centroidForCode(code: TypeCode): AxisProfile {
    const letters = lettersOfCode(code);
    const valueFor = (axis: PersonalityAxis) =>
        letters[axis] === TYPE_LETTERS[axis].high ? CENTROID_HIGH : CENTROID_LOW;
    return {
        horizon: valueFor('horizon'),
        signal: valueFor('signal'),
        contrarian: valueFor('contrarian'),
        cadence: valueFor('cadence'),
    };
}

export function codeFromProfile(profile: AxisProfile): TypeCode {
    return TYPE_SLOT_ORDER.map((axis) => letterForValue(axis, profile[axis])).join('') as TypeCode;
}

export interface NeighbourResult {
    code: TypeCode;
    axis: PersonalityAxis;
    /** The letter you would carry in the neighbouring cell. */
    letter: TypeLetter;
}

/**
 * The neighbouring type is the cell you would occupy if your weakest letter
 * flipped. Ties resolve in slot order (horizon, signal, stance, tempo).
 */
export function neighbourForProfile(profile: AxisProfile): NeighbourResult | null {
    if (TYPE_SLOT_ORDER.length === 0) return null;

    let weakest: PersonalityAxis = TYPE_SLOT_ORDER[0];
    let weakestMargin = Number.POSITIVE_INFINITY;
    for (const axis of TYPE_SLOT_ORDER) {
        const margin = Math.abs(profile[axis] - 50);
        if (margin < weakestMargin) {
            weakestMargin = margin;
            weakest = axis;
        }
    }

    const letters = lettersOfCode(codeFromProfile(profile));
    const flipped =
        letters[weakest] === TYPE_LETTERS[weakest].high
            ? TYPE_LETTERS[weakest].low
            : TYPE_LETTERS[weakest].high;
    const neighbourCode = TYPE_SLOT_ORDER.map((axis) =>
        axis === weakest ? flipped : letters[axis],
    ).join('');

    return {
        code: neighbourCode as TypeCode,
        axis: weakest,
        letter: flipped as TypeLetter,
    };
}
