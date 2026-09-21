export interface SplitPromptResult {
    header: string;
    mutable: string;
    footer: string;
    isSplit: boolean;
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

    // Daily Predictor prompts: Header ends after Zero-Mean Mandate
    const lastMandateIdx = promptText.lastIndexOf('Avoid positive-framing bias.');
    if (lastMandateIdx !== -1 && lastMandateIdx < footerStart) {
        const firstMandateIdx = promptText.indexOf('Avoid positive-framing bias.');
        const mandateLen = 'Avoid positive-framing bias.'.length;
        const header = promptText.slice(0, firstMandateIdx + mandateLen).trim();
        let mutable = promptText.slice(lastMandateIdx + mandateLen, footerStart).trim();
        const footer = promptText.slice(footerStart).trim();

        // Defensive cleanup of any leftover duplicate headers in mutable
        mutable = mutable
            .replace(
                /You are an elite quantitative macro trader[\s\S]*?Avoid positive-framing bias\.\s*/g,
                '',
            )
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
