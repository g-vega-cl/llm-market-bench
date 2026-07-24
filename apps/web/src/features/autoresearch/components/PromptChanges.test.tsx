import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PromptChanges } from './PromptChanges';

describe('PromptChanges', () => {
    const mockCurrentExperiment = {
        id: '1',
        variant_tag: 'V1.1',
        parent_tag: 'V1.0',
        prompt_content: 'line 1\nline 2\nline 3',
        experiment_type: 'radical',
    } as unknown as PromptExperiment;

    const mockParentExperiment = {
        id: '2',
        variant_tag: 'V1.0',
        prompt_content: 'line 1\nline 3',
        experiment_type: 'baseline',
    } as unknown as PromptExperiment;

    it('renders initial baseline message when parent experiment is missing (baseline type)', () => {
        const baselineExp = {
            ...mockCurrentExperiment,
            experiment_type: 'baseline',
        } as unknown as PromptExperiment;
        render(<PromptChanges experiment={baselineExp} parentExperiment={null} />);

        expect(screen.getByText(/Initial baseline prompt/i)).toBeInTheDocument();
        expect(
            screen.getByText(/No previous variant is available to compare/i),
        ).toBeInTheDocument();
    });

    it('renders no parent prompt message when parent experiment is missing (non-baseline type)', () => {
        render(<PromptChanges experiment={mockCurrentExperiment} parentExperiment={null} />);

        expect(screen.getByText(/No parent prompt/i)).toBeInTheDocument();
        expect(
            screen.getByText(
                /This experiment does not have a registered parent variant to compare against/i,
            ),
        ).toBeInTheDocument();
    });

    it('renders the diff when parent experiment is present', () => {
        render(
            <PromptChanges
                experiment={mockCurrentExperiment}
                parentExperiment={mockParentExperiment}
            />,
        );

        // Header and elements
        expect(screen.getByText('Prompt Changes')).toBeInTheDocument();
        expect(screen.getByText('Show Full Prompt Diff')).toBeInTheDocument();

        // Unchanged lines should NOT be visible by default
        expect(screen.queryByText('line 1')).not.toBeInTheDocument();
        expect(screen.queryByText('line 3')).not.toBeInTheDocument();

        // Line 2 is added
        const addedLine = screen.getByText('+ line 2');
        expect(addedLine).toBeInTheDocument();
        expect(addedLine.className).toContain('text-emerald-400');
    });

    it('toggles visibility of unchanged lines when toggle button is clicked', () => {
        render(
            <PromptChanges
                experiment={mockCurrentExperiment}
                parentExperiment={mockParentExperiment}
            />,
        );

        // Unchanged lines are hidden initially
        expect(screen.queryByText('line 1')).not.toBeInTheDocument();
        expect(screen.queryByText('line 3')).not.toBeInTheDocument();

        const toggleBtn = screen.getByText('Show Full Prompt Diff');
        fireEvent.click(toggleBtn);

        // Toggle text should update to Show Changes Only
        expect(screen.getByText('Show Changes Only')).toBeInTheDocument();

        // Unchanged lines should now be visible
        expect(screen.getByText('line 1')).toBeInTheDocument();
        expect(screen.getByText('line 3')).toBeInTheDocument();

        // Added lines should still be visible
        expect(screen.getByText('+ line 2')).toBeInTheDocument();
    });
});
