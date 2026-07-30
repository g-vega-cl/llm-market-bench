import { describe, expect, it } from 'vitest';
import { splitPromptSections } from './promptSections';

describe('splitPromptSections', () => {
    it('correctly splits a standard full prompt into header, mutable, and footer', () => {
        const fullPrompt = `You are a hedge fund trading algorithm.
=== CRITICAL TOOL USAGE REQUIREMENTS ===
This is a HARD REQUIREMENT. No exceptions.

=== REASONING RIGOR: THE "5 WHYS" & REASONING TOOLBOX ===
1. 5 Whys (Causal Depth)
=== SOPHISTICATED TRADING LOGIC ===
1. Focus on high probability trades.

=== SMA MANAGEMENT RULES ===
1. SMA is your Buying Power High Water Mark.
=== OUTPUT FORMAT: TRADING SIGNALS ===
Return the result as a structured JSON object containing a list of 'decisions'.`;

        const result = splitPromptSections(fullPrompt);

        expect(result.isSplit).toBe(true);
        expect(result.header).toContain('You are a hedge fund trading algorithm.');
        expect(result.header).toContain('CRITICAL TOOL USAGE REQUIREMENTS');
        expect(result.mutable).toContain('REASONING RIGOR');
        expect(result.mutable).toContain('SOPHISTICATED TRADING LOGIC');
        expect(result.footer).toContain('SMA MANAGEMENT RULES');
        expect(result.footer).toContain(
            "Return the result as a structured JSON object containing a list of 'decisions'.",
        );
    });

    it('handles prompts with fallback strategy markers like CALENDAR & SEASONAL STRATEGIES', () => {
        const fullPrompt = `System instructions...

=== CALENDAR & SEASONAL STRATEGIES ===
1. Turn of the month strategy.

=== SMA MANAGEMENT RULES ===
1. Rules here.`;

        const result = splitPromptSections(fullPrompt);

        expect(result.isSplit).toBe(true);
        expect(result.header).toContain('System instructions...');
        expect(result.mutable).toContain('CALENDAR & SEASONAL STRATEGIES');
        expect(result.footer).toContain('SMA MANAGEMENT RULES');
    });

    it('falls back gracefully to full prompt if section markers are missing', () => {
        const customPrompt = `This is a custom unstructured trading prompt.`;

        const result = splitPromptSections(customPrompt);

        expect(result.isSplit).toBe(false);
        expect(result.header).toBe('');
        expect(result.mutable).toBe('This is a custom unstructured trading prompt.');
        expect(result.footer).toBe('');
    });
});
