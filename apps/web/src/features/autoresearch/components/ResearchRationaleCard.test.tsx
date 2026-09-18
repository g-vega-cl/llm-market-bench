import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ResearchRationaleCard } from './ResearchRationaleCard';

describe('ResearchRationaleCard', () => {
    it('renders change description, experiment type, and normalized reasoning', () => {
        const mockExperiment = {
            change_description: 'Tightened trailing profit ratchet.',
            experiment_type: 'incremental',
            research_output: {
                research_reasoning: 'Prior run liquidated winners too early.',
                confidence: 85,
                research_insight: 'Momentum runners must be held past the first resistance break.',
                hypothesis: 'Trailing profit stops will improve portfolio excess return by 1.2%.',
            },
        } as unknown as PromptExperiment;

        render(<ResearchRationaleCard experiment={mockExperiment} />);

        expect(screen.getByText('Meta-Researcher Rationale & Conviction')).toBeInTheDocument();
        expect(screen.getByText('"Tightened trailing profit ratchet."')).toBeInTheDocument();
        expect(screen.getByText('85%')).toBeInTheDocument();
        expect(screen.getByText('Prior run liquidated winners too early.')).toBeInTheDocument();
        expect(
            screen.getByText('Trailing profit stops will improve portfolio excess return by 1.2%.'),
        ).toBeInTheDocument();
        expect(
            screen.getByText('"Momentum runners must be held past the first resistance break."'),
        ).toBeInTheDocument();
    });

    it('falls back to thought_process if research_reasoning is absent', () => {
        const mockExperiment = {
            change_description: 'Legacy experiment',
            experiment_type: 'baseline',
            research_output: {
                thought_process: 'Legacy analytical reasoning text.',
            },
        } as unknown as PromptExperiment;

        render(<ResearchRationaleCard experiment={mockExperiment} />);
        expect(screen.getByText('Legacy analytical reasoning text.')).toBeInTheDocument();
    });
});
