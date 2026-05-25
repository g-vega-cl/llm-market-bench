import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ExperimentList } from './ExperimentList';

describe('ExperimentList', () => {
    it('renders dates stably without relying on system locale or timezone', () => {
        const mockExperiments = [
            {
                id: 'exp-1',
                variant_tag: 'v1.0',
                experiment_type: 'radical',
                week_start: '2026-05-18',
                week_end: '2026-05-24',
                metrics: { score: 1.5 },
                status: 'active',
            },
        ] as unknown as PromptExperiment[];

        const onSelect = () => {};

        render(
            <ExperimentList experiments={mockExperiments} onSelect={onSelect} selectedId="exp-1" />,
        );

        // This expects the date block to display 'May 18, 2026 - May 24, 2026'
        // stably regardless of locale or timezone offset.
        expect(screen.getByText('May 18, 2026 - May 24, 2026')).toBeInTheDocument();
    });
});
