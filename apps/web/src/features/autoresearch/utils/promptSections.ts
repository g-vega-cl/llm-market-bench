export interface SplitPromptResult {
    header: string;
    mutable: string;
    footer: string;
    isSplit: boolean;
}

/**
 * Split a full CORE_ANALYSIS_SYSTEM_PROMPT into Header, Mutable Strategies, and Footer.
 * Mirrors the logic from apps/engine/core/llm/prompts.py:split_prompt
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

    // Identify start of Mutable Strategies (the only section autoresearch evolves)
    const mutableMarkers = [
        '=== REASONING RIGOR',
        '=== CALENDAR & SEASONAL',
        '=== SOPHISTICATED TRADING LOGIC',
    ];

    let mutableStart = -1;
    for (const marker of mutableMarkers) {
        const idx = promptText.indexOf(marker);
        if (idx !== -1 && (mutableStart === -1 || idx < mutableStart)) {
            mutableStart = idx;
        }
    }

    if (mutableStart !== -1 && footerStart !== -1 && mutableStart < footerStart) {
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
