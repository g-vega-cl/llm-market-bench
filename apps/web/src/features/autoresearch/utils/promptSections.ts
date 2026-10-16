export interface SplitPromptResult {
    header: string;
    mutable: string;
    footer: string;
    isSplit: boolean;
}

const DAILY_CONTEXT_MARKER = '=== AVAILABLE MARKET CONTEXT ===';
const FROZEN_IDENTITY_LINE_PREFIXES = [
    'You are an elite quantitative macro trader',
    "Your goal is to predict whether today's 4:00 PM ET Close",
];

/** Index just past the context block starting at markerIdx: first blank line or next `===` heading. */
function contextBlockEnd(text: string, markerIdx: number): number {
    let pos = text.indexOf('\n', markerIdx);
    while (pos !== -1) {
        const next = text.indexOf('\n', pos + 1);
        const line = text.slice(pos + 1, next === -1 ? text.length : next);
        if (!line.trim() || line.startsWith('===')) {
            return pos;
        }
        pos = next;
    }
    return text.length;
}

/**
 * Split a full CORE_ANALYSIS_SYSTEM_PROMPT or DAILY_PREDICTOR_PROMPT into Header, Mutable Strategies, and Footer.
 * Mirrors the logic from apps/engine/core/llm/prompts.py:split_prompt and daily_predictor_prompts.py:split_daily_predictor_prompt
 */
export function splitPromptSections(promptText: string): SplitPromptResult {
    if (!promptText) {
        return { header: '', mutable: '', footer: '', isSplit: false };
    }

    // Identify start of Footer (un-editable system constraints & output JSON schema)
    let footerStart = promptText.indexOf('=== SMA MANAGEMENT RULES ===');
    if (footerStart === -1) {
        footerStart = promptText.indexOf('=== OUTPUT FORMAT: TRADING SIGNALS ===');
    }
    if (footerStart === -1) {
        footerStart = promptText.indexOf('=== REQUIRED OUTPUT FORMAT ===');
    }

    if (footerStart === -1) {
        return {
            header: '',
            mutable: promptText.trim(),
            footer: '',
            isSplit: false,
        };
    }

    // Daily Predictor prompts: Header = trader identity + available market context.
    // Everything after the context block (including base-rate / anti-bias guidance) is mutable.
    const body = promptText.slice(0, footerStart);
    const firstContextIdx = body.indexOf(DAILY_CONTEXT_MARKER);
    if (firstContextIdx !== -1) {
        const lastContextIdx = body.lastIndexOf(DAILY_CONTEXT_MARKER);
        const header = body.slice(0, contextBlockEnd(body, firstContextIdx)).trim();
        const footer = promptText.slice(footerStart).trim();

        // Last context block wins so duplicated headers are dropped; also drop stray identity lines
        const mutable = body
            .slice(contextBlockEnd(body, lastContextIdx))
            .split('\n')
            .filter((line) => !FROZEN_IDENTITY_LINE_PREFIXES.some((p) => line.startsWith(p)))
            .join('\n')
            .trim();

        return {
            header,
            mutable,
            footer,
            isSplit: true,
        };
    }

    // Identify start of Mutable Strategies (the only section autoresearch evolves)
    const mutableMarkers = [
        '=== REASONING RIGOR',
        '=== CALENDAR & SEASONAL',
        '=== SOPHISTICATED TRADING LOGIC',
        '=== ANALYTICAL STRATEGY INSTRUCTIONS ===',
        '=== INSTRUCTIONS ===',
    ];

    let mutableStart = -1;
    for (const marker of mutableMarkers) {
        const idx = promptText.indexOf(marker);
        if (idx !== -1 && (mutableStart === -1 || idx < mutableStart)) {
            mutableStart = idx;
        }
    }

    if (mutableStart !== -1 && mutableStart < footerStart) {
        const header = promptText.slice(0, mutableStart).trim();
        const mutable = promptText.slice(mutableStart, footerStart).trim();
        const footer = promptText.slice(footerStart).trim();

        return {
            header,
            mutable,
            footer,
            isSplit: true,
        };
    }

    // Fallback if standard headers/footers are not detected
    return {
        header: '',
        mutable: promptText.trim(),
        footer: '',
        isSplit: false,
    };
}
