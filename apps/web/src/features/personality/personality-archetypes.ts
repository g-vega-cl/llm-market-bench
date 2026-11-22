import { LONG_ARCHETYPES } from './personality-archetypes-long';
import { QUICK_ARCHETYPES } from './personality-archetypes-quick';
import type { AxisProfile } from './personality-axes';
import { centroidForCode, TYPE_CODES, type TypeCode } from './personality-type-grid';

/**
 * All 16 cells, in grid order (rows LV/LN/QV/QN, columns FP/FR/MP/MR).
 * Every cell owns exactly one archetype and one starter recipe.
 */
export const ARCHETYPE_IDS = [
    'value-compounder',
    'value-rotator',
    'compound-buyer',
    'quality-rotator',
    'contrarian-diver',
    'systems-architect',
    'catalyst-holder',
    'catalyst-quant',
    'bargain-snapper',
    'deep-value-trader',
    'value-scalper',
    'multiple-rotator',
    'headline-fader',
    'news-contrarian',
    'print-trader',
    'news-surfer',
] as const;

export type ArchetypeId = (typeof ARCHETYPE_IDS)[number];

export interface InvestingArchetype {
    id: ArchetypeId;
    /** Fixed-order four-letter code this archetype owns. */
    code: TypeCode;
    title: string;
    tagline: string;
    summary: string;
    strengths: [string, string, string];
    watchout: string;
    recipeName: string;
    builderIdeaPrompt: string;
    idealProfile: AxisProfile;
}

export interface TypeCell {
    code: TypeCode;
    centroid: AxisProfile;
    /** Archetype that owns this cell. */
    archetypeId?: ArchetypeId;
}

const CATALOGUE: readonly InvestingArchetype[] = [...LONG_ARCHETYPES, ...QUICK_ARCHETYPES];

export const ARCHETYPES: Record<ArchetypeId, InvestingArchetype> = Object.fromEntries(
    CATALOGUE.map((archetype) => [archetype.id, archetype]),
) as Record<ArchetypeId, InvestingArchetype>;

export const TYPE_GRID: TypeCell[] = TYPE_CODES.map((code) => ({
    code,
    centroid: centroidForCode(code),
    archetypeId: ARCHETYPE_IDS.find((id) => ARCHETYPES[id].code === code),
}));

/**
 * A missing, duplicated or unknown code would silently merge or orphan a cell,
 * so the whole grid is validated eagerly at module load rather than at render.
 */
export function assertValidArchetypeGrid(): void {
    if (CATALOGUE.length !== ARCHETYPE_IDS.length) {
        throw new Error(
            `Archetype catalogue has ${String(CATALOGUE.length)} entries for ${String(ARCHETYPE_IDS.length)} ids`,
        );
    }

    const claimed = new Set<string>();
    for (const id of ARCHETYPE_IDS) {
        const archetype = ARCHETYPES[id];
        if (!archetype) {
            throw new Error(`Missing archetype for id "${id}"`);
        }
        if (claimed.has(archetype.code)) {
            throw new Error(`Two archetypes claim type code "${archetype.code}"`);
        }
        if (!TYPE_CODES.includes(archetype.code)) {
            throw new Error(`Archetype "${id}" claims unknown type code "${archetype.code}"`);
        }
        claimed.add(archetype.code);
    }

    for (const code of TYPE_CODES) {
        if (!claimed.has(code)) {
            throw new Error(`Type code "${code}" has no archetype`);
        }
    }
}

export function isValidArchetypeId(value: unknown): value is ArchetypeId {
    return typeof value === 'string' && (ARCHETYPE_IDS as readonly string[]).includes(value);
}
