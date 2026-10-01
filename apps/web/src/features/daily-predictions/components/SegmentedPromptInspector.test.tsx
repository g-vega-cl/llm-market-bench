import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SegmentedPromptInspector } from './SegmentedPromptInspector';

describe('SegmentedPromptInspector', () => {
    it('renders un-split prompt with wrapper', () => {
        render(<SegmentedPromptInspector promptContent="Simple un-segmented prompt." />);
        expect(screen.getByText('The Predictor Prompt')).toBeInTheDocument();
        expect(screen.getByText('Simple un-segmented prompt.')).toBeInTheDocument();
    });

    it('renders segmented sections with badges and pre tags', () => {
        const splitPrompt = `=== ZERO-MEAN BASE RATE & ANTI-BIAS MANDATE ===
Engine Constraints

=== ANALYTICAL STRATEGY INSTRUCTIONS ===
Intraday Strategy

=== REQUIRED OUTPUT FORMAT ===
JSON schema`;

        const { container } = render(<SegmentedPromptInspector promptContent={splitPrompt} />);

        expect(screen.getByText(/1\. Engine Constraints & Anti-Bias Mandate/i)).toBeInTheDocument();
        expect(
            screen.getByText(/2\. Intraday Trading Strategy & Analysis Rules/i),
        ).toBeInTheDocument();
        expect(screen.getByText(/3\. Risk Rules & Output JSON Schema/i)).toBeInTheDocument();

        const preElements = container.querySelectorAll('pre');
        expect(preElements.length).toBe(3);
        for (const pre of preElements) {
            expect(pre.className).toContain('whitespace-pre-wrap');
            expect(pre.className).toContain('break-words');
        }
    });
});
