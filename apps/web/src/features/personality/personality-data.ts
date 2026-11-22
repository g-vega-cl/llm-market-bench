import type { WorldId } from '../home/backdrop/voxel-world';
import { STARTER_RECIPES } from '../recipes/starter-templates';
import type { PushStrategy } from '../recipes/types';
import { PERSONALITY_QUESTIONS, type QuizOption, type QuizQuestion } from './personality-questions';

export { PERSONALITY_QUESTIONS, type QuizOption, type QuizQuestion };

export const PERSONALITY_AXES = ['horizon', 'signal', 'contrarian', 'cadence'] as const;

export type PersonalityAxis = (typeof PERSONALITY_AXES)[number];

export interface AxisDefinition {
    id: PersonalityAxis;
    label: string;
    lowLabel: string;
    highLabel: string;
}

export const AXIS_DEFINITIONS: AxisDefinition[] = [
    {
        id: 'horizon',
        label: 'Patience & Horizon',
        lowLabel: 'Session Swings',
        highLabel: 'Multi-Quarter Thesis',
    },
    {
        id: 'signal',
        label: 'Signal Anchor',
        lowLabel: 'Balance Sheet & Value',
        highLabel: 'Live Headlines & Catalysts',
    },
    {
        id: 'contrarian',
        label: 'Crowd Stance',
        lowLabel: 'Ride Trend Confirmation',
        highLabel: 'Fade Panic & Euphoria',
    },
    {
        id: 'cadence',
        label: 'Execution Tempo',
        lowLabel: 'Selective Patience',
        highLabel: 'Active Rotation',
    },
];

export const ARCHETYPE_IDS = [
    'value-compounder',
    'news-surfer',
    'contrarian-diver',
    'catalyst-quant',
    'systems-architect',
] as const;

export type ArchetypeId = (typeof ARCHETYPE_IDS)[number];

export type AxisProfile = Record<PersonalityAxis, number>;

export interface InvestingArchetype {
    id: ArchetypeId;
    title: string;
    tagline: string;
    summary: string;
    strengths: [string, string, string];
    watchout: string;
    worldId: WorldId;
    recipeName: string;
    builderIdeaPrompt: string;
    idealProfile: AxisProfile;
}

export const ARCHETYPES: Record<ArchetypeId, InvestingArchetype> = {
    'value-compounder': {
        id: 'value-compounder',
        title: 'The Patient Compounder',
        tagline:
            'Ignores noisy headlines in favor of cash flow, valuation discipline, and clean trends.',
        summary:
            'You treat every trade like owning a durable business. Noise gets tuned out; a missed hype rally bothers you far less than overpaying for weak unit economics. You win by sitting comfortably on your hands when nothing clears your bar.',
        strengths: [
            'Resists FOMO during speculative headline spikes',
            'Anchors decisions to verifiable free cash flow and multiples',
            'Stays calm holding winners across multi-week drawdowns',
        ],
        watchout: 'May hesitate to cut or rotate quickly when a macro regime genuinely flips.',
        worldId: 'sakura-garden',
        recipeName: 'Quality Value Screener',
        builderIdeaPrompt:
            'Build a quality value bot that ignores news headlines, screens for P/E under 28, positive free cash flow, positive MACD, and price below 90% of its 52-week high, holding cash when nothing clears every rule.',
        idealProfile: { horizon: 90, signal: 12, contrarian: 58, cadence: 16 },
    },
    'news-surfer': {
        id: 'news-surfer',
        title: 'The Headline Surfer',
        tagline:
            'Reads policy shocks and sector catalysts first, riding fresh narrative repricing early.',
        summary:
            'You watch where capital is forced to reprice right now — tariffs, chip bans, breakthrough launches — and pair headline speed with guardrail technical checks so you surf waves without getting trapped at exhausted highs.',
        strengths: [
            'Spreads risk across liquid high-velocity themes fast',
            'Connects macro news directly to second-order equity movers',
            'Cuts stale narratives promptly instead of bags-holding',
        ],
        watchout:
            'Avoid chasing extended RSI extremes once everybody already agrees on the headline.',
        worldId: 'magma-forge',
        recipeName: 'Trump & Chips News Momentum',
        builderIdeaPrompt:
            'Build a news momentum bot scanning 48h chip and policy headlines paired with tariff memories, verifying P/E under 45 and RSI under 70 before entering.',
        idealProfile: { horizon: 18, signal: 92, contrarian: 16, cadence: 90 },
    },
    'contrarian-diver': {
        id: 'contrarian-diver',
        title: 'The Contrarian Diver',
        tagline:
            'Buys orderly liquidation panic when sentiment overshoots and sells into crowd euphoria.',
        summary:
            'When the tape panics on recycled headlines, you measure volume structure and barometer extremes rather than joining the stampede. You would rather buy exhaustion below VWAP than chase consensus winners.',
        strengths: [
            'Comfortable buying high-quality names during emotional flushes',
            'Maintains strict distinction between structural breaks and panic',
            'Takes profits automatically into euphoric consensus peaks',
        ],
        watchout:
            'Requires hard discipline against catching falling knives when fundamentals actually break.',
        worldId: 'bioluminescent-reef',
        recipeName: 'Contrarian Sentiment Fader',
        builderIdeaPrompt:
            'Build a contrarian mean-reversion bot that checks the market-feeling barometer, looks for oversold RSI below 35 and price below VWAP on orderly volume with no broken fundamentals, and exits profitable positions into euphoria.',
        idealProfile: { horizon: 56, signal: 58, contrarian: 94, cadence: 44 },
    },
    'catalyst-quant': {
        id: 'catalyst-quant',
        title: 'The Catalyst Quant',
        tagline:
            'Finds multi-quarter EPS surprise streaks and trades the clean post-print drift window.',
        summary:
            'You trust measurable repeatability over vibes: earnings beats backed by real guidance raises, confirmed by relative volume above 1.5x and positive MACD — while skipping names that already spiked out of bounds on the open.',
        strengths: [
            'Combines fundamental surprise history with crisp technical confirmation',
            'Avoids noisy mid-quarter churn outside verifiable event windows',
            'Follows pre-committed exit rules when drift stalls',
        ],
        watchout: 'Stay mindful of correlated sector exposure during peak earnings weeks.',
        worldId: 'sky-observatory',
        recipeName: 'Earnings Catalyst Hunter',
        builderIdeaPrompt:
            'Build an earnings catalyst drift bot checking 4 quarters of EPS surprise history and management guidance over 72h earnings news, filtering for RVOL above 1.5 and positive MACD while skipping names already up over 8%.',
        idealProfile: { horizon: 48, signal: 68, contrarian: 38, cadence: 64 },
    },
    'systems-architect': {
        id: 'systems-architect',
        title: 'The Systems Architect',
        tagline:
            'Runs a full tool-first research loop balancing catalysts, memory, and thesis audits.',
        summary:
            'You value intellectual honesty above any single indicator. Before entering or holding a position, every open thesis gets audited against quotes, price history, news transmission chains, and past post-mortems on every slot.',
        strengths: [
            'Forces explicit profit mechanisms before allocating capital',
            'Audits existing holdings continuously instead of holding by inertia',
            'Synthesizes macro context, valuation, and technical state uniformly',
        ],
        watchout:
            'Over-researching ambiguous setups can reduce turnover if thresholds get too tight.',
        worldId: 'cedar-sanctuary',
        recipeName: 'Claude Agent Portfolio Mirror',
        builderIdeaPrompt:
            'Build a balanced portfolio mirror bot with 4x25% long sizing that traces catalyst-to-earnings chains, audits open positions every slot to exit broken theses, and requires RSI below 75, positive VWAP spread, and RVOL above 1.2.',
        idealProfile: { horizon: 64, signal: 50, contrarian: 52, cadence: 50 },
    },
};

export function isValidArchetypeId(value: unknown): value is ArchetypeId {
    return typeof value === 'string' && (ARCHETYPE_IDS as readonly string[]).includes(value);
}

export interface ArchetypeMatch {
    archetype: InvestingArchetype;
    recipe: PushStrategy;
    fitPercent: number;
    distance: number;
}

export interface QuizScoreResult {
    profile: AxisProfile;
    primary: ArchetypeMatch;
    runnerUp: ArchetypeMatch;
    rankings: ArchetypeMatch[];
    answeredCount: number;
}

const recipeByName = new Map<string, PushStrategy>(
    STARTER_RECIPES.map((recipe) => [recipe.name, recipe]),
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

function rankArchetypesForProfile(
    profile: AxisProfile,
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
        return ARCHETYPE_IDS.indexOf(a.archetype.id) - ARCHETYPE_IDS.indexOf(b.archetype.id);
    });
}

export function scorePersonalityQuiz(answers: Partial<Record<string, string>>): QuizScoreResult {
    const { answeredCount, rawSum, minBound, maxBound } = accumulateAxisTotals(answers);
    const profile = normalizeAxisProfile(answeredCount, rawSum, minBound, maxBound);
    const rankings = rankArchetypesForProfile(profile);
    return {
        profile,
        primary: rankings[0],
        runnerUp: rankings[1],
        rankings,
        answeredCount,
    };
}

export function buildSharedArchetypeResult(archetypeId: ArchetypeId): QuizScoreResult {
    const profile = { ...ARCHETYPES[archetypeId].idealProfile };
    const rankings = rankArchetypesForProfile(profile, archetypeId);
    return {
        profile,
        primary: rankings[0],
        runnerUp: rankings[1],
        rankings,
        answeredCount: PERSONALITY_QUESTIONS.length,
    };
}
