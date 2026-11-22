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
            'You treat every trade like owning a durable business. Noise gets tuned out; missed hype bothers you less than overpaying, so you wait for clear value.',
        strengths: [
            'Resists FOMO during speculative headline spikes',
            'Anchors decisions to free cash flow and multiples',
            'Stays calm holding winners across slow pullbacks',
        ],
        watchout: 'May hesitate to cut or rotate quickly when a macro regime genuinely flips.',
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
            'You track where capital must reprice right now — tariffs, chips, launches — pairing headline velocity with guardrails so you never chase exhausted highs.',
        strengths: [
            'Spreads risk across liquid high-velocity themes fast',
            'Maps macro news directly to second-order equity movers',
            'Cuts stale narratives promptly instead of bag-holding',
        ],
        watchout:
            'Avoid chasing extended RSI extremes once everybody already agrees on the headline.',
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
            'When the tape panics on recycled headlines, you read sentiment extremes and volume structure — buying exhaustion below VWAP instead of herd consensus.',
        strengths: [
            'Comfortable buying quality names during sudden flushes',
            'Separates structural balance-sheet breaks from panic',
            'Takes profits cleanly into euphoric consensus peaks',
        ],
        watchout:
            'Requires hard discipline against catching falling knives when fundamentals actually break.',
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
            'You trust measurable repeatability over vibes: EPS beats backed by guidance raises, RVOL above 1.5x, and positive MACD while skipping extended spikes.',
        strengths: [
            'Combines surprise history with technical confirmation',
            'Avoids noisy churn outside verified event windows',
            'Follows pre-committed exit rules when drift stalls',
        ],
        watchout: 'Stay mindful of correlated sector exposure during peak earnings weeks.',
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
            'You value intellectual honesty over any single signal. Every open thesis is audited against quotes, price history, news chains, and past post-mortems.',
        strengths: [
            'Forces explicit profit logic before risking capital',
            'Audits existing holdings continuously for broken rules',
            'Blends macro news, valuation, and technical structure',
        ],
        watchout:
            'Over-researching ambiguous setups can reduce turnover if thresholds get too tight.',
        recipeName: 'Claude Agent Portfolio Mirror',
        builderIdeaPrompt:
            'Build a balanced portfolio mirror bot with 4x25% long sizing that traces catalyst-to-earnings chains, audits open positions every slot to exit broken theses, and requires RSI below 75, positive VWAP spread, and RVOL above 1.2.',
        idealProfile: { horizon: 64, signal: 50, contrarian: 52, cadence: 50 },
    },
};

function formatRuleLabel(metric: string, operator: string, target: string): string {
    if (metric === 'price_52w_pct') return `52w ${operator} ${target}%`;
    if (metric === 'Price vs VWAP') return `VWAP ${operator} ${target}`;
    return `${metric} ${operator} ${target}`;
}

/**
 * Derives a compact, drift-free single-line execution summary directly from
 * all canonical blocks in `packages/config/starter-recipes.json`.
 */
export function formatRecipeExecutionSpec(recipe: PushStrategy): string {
    const blocks = recipe.stages[0]?.blocks ?? [];
    const newsBlocks = blocks.filter((block) => block.type === 'news');
    const memoryBlocks = blocks.filter((block) => block.type === 'memories');
    const technicalBlocks = blocks.filter((block) => block.type === 'technicals');

    const segments: string[] = [];
    if (newsBlocks.length > 0) {
        for (const n of newsBlocks) segments.push(`News ${n.recency_hours}h`);
    } else {
        segments.push('News Off');
    }
    for (const mem of memoryBlocks) {
        segments.push(`Memory ${mem.recency_hours}h`);
    }
    const allRules = technicalBlocks.flatMap((t) => t.rules);
    if (allRules.length > 0) {
        const formattedRules = allRules
            .map((r) => formatRuleLabel(r.metric, r.operator, r.target))
            .join(' · ');
        segments.push(`Rules: ${formattedRules}`);
    }
    return segments.join(' · ');
}

function compactRuleToken(metric: string, operator: string, target: string): string {
    if (metric === 'price_52w_pct') return `${operator}${target}% 52w`;
    if (metric === 'Price vs VWAP') return `VWAP${operator}${target}`;
    return `${metric}${operator}${target}`;
}

const CORE_GATE_MAX_CHARS = 14;

function fitNewsCoreGate(prefix: string, compactRules: string[]): string {
    const preferred = compactRules.find((r) => r.startsWith('RVOL')) ?? compactRules[0];
    if (preferred) {
        const candidate = `${prefix} · ${preferred}`;
        if (candidate.length <= CORE_GATE_MAX_CHARS) return candidate;
        const tight = `${prefix}·${preferred.replace(/\s+/g, '')}`;
        if (tight.length <= CORE_GATE_MAX_CHARS) return tight;
    }
    return `${prefix} News`.slice(0, CORE_GATE_MAX_CHARS);
}

/**
 * Derives a compact badge token (structurally bounded to <= 14 chars) directly
 * from starter recipe blocks so badges stay single-line at 360px mobile widths.
 */
export function summarizeRecipeCoreGate(recipe: PushStrategy): string {
    const blocks = recipe.stages[0]?.blocks ?? [];
    const news = blocks.find((block) => block.type === 'news');
    const compactRules = blocks
        .filter((block) => block.type === 'technicals')
        .flatMap((block) =>
            block.rules.map((r) => compactRuleToken(r.metric, r.operator, r.target)),
        );

    if (news) {
        return fitNewsCoreGate(`${news.recency_hours}h`, compactRules);
    }

    if (compactRules.length > 0) {
        let acc = compactRules[0];
        for (let i = 1; i < compactRules.length; i++) {
            const next = `${acc} · ${compactRules[i]}`;
            if (next.length > CORE_GATE_MAX_CHARS) break;
            acc = next;
        }
        return acc.slice(0, CORE_GATE_MAX_CHARS);
    }

    return `${recipe.stages[0]?.selected_tools.length ?? 0} tool checks`.slice(
        0,
        CORE_GATE_MAX_CHARS,
    );
}

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
